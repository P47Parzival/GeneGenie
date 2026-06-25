"""ClinVar lookups against a tabix-indexed clinvar.vcf.gz.

Rather than the compiled cyvcf2/pysam bindings (no wheels on very new Pythons),
we shell out to the `tabix` CLI (htslib), which is installed system-wide on the
EC2 box. tabix does a fast, index-backed region query; we parse the VCF text.

ClinVar INFO fields we care about:
  - GENEINFO : "BRCA1:672" (gene symbol:NCBI gene id, '|'-separated for multi)
  - CLNSIG   : clinical significance, e.g. "Pathogenic"
  - CLNDN    : disease name(s), '|'-separated, words joined by '_'
  - RS       : dbSNP rsID (numeric, no 'rs' prefix)
"""

from __future__ import annotations

import subprocess

from . import acmg, population
from .models import Annotation, VariantQuery


def _norm_chrom(chrom: str) -> str:
    """ClinVar GRCh38 VCF uses bare chromosome names ('17', 'X', 'MT')."""
    c = chrom.strip()
    if c.lower().startswith("chr"):
        c = c[3:]
    if c in {"M", "m"}:
        c = "MT"
    return c


def _parse_info(info: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for part in info.split(";"):
        if not part:
            continue
        key, _, value = part.partition("=")
        fields[key] = value if value else "true"
    return fields


class ClinVarAnnotator:
    """Wraps a tabix-indexed ClinVar VCF for region-based annotation."""

    def __init__(self, dataset, tabix_bin: str = "tabix", dbsnp=None, gnomad=None, onekg=None):
        self.dataset = dataset
        self.vcf_path = dataset.local_path if dataset else None
        self.tabix_bin = tabix_bin
        # Optional DbSnpLookup for rsID enrichment when ClinVar has no match.
        self.dbsnp = dbsnp
        # Optional GnomadLookup for population allele frequencies (AF, AF_sas).
        self.gnomad = gnomad
        # Optional OneKGenomesSAS for 1000G SAS frequencies (Week 6).
        self.onekg = onekg

    @property
    def available(self) -> bool:
        return bool(self.dataset and self.dataset.available())

    def _query_region(self, chrom: str, pos: int) -> list[list[str]]:
        region = f"{chrom}:{pos}-{pos}"
        proc = subprocess.run(
            [self.tabix_bin, str(self.vcf_path), region],
            capture_output=True,
            text=True,
            check=True,
        )
        rows: list[list[str]] = []
        for line in proc.stdout.splitlines():
            if line and not line.startswith("#"):
                rows.append(line.split("\t"))
        return rows

    def _assemble(
        self,
        q: VariantQuery,
        chrom: str,
        clinvar_rows: list[list[str]],
        gnomad_freqs: tuple,
        onekg_freqs: tuple,
        dbsnp_rsid: str | None,
        gnomad_covered: bool,
        onekg_covered: bool,
    ) -> Annotation:
        result = Annotation(chrom=chrom, pos=q.pos, ref=q.ref, alt=q.alt)

        for cols in clinvar_rows:
            if len(cols) < 8:
                continue
            if int(cols[1]) != q.pos or cols[3] != q.ref or q.alt not in cols[4].split(","):
                continue
            info = _parse_info(cols[7])
            geneinfo = info.get("GENEINFO")
            rs = info.get("RS")
            disease = info.get("CLNDN")
            result.gene = geneinfo.split(":")[0] if geneinfo else None
            result.variant = f"rs{rs}" if rs else None
            result.significance = info.get("CLNSIG")
            result.review_status = info.get("CLNREVSTAT")
            result.disease = disease.replace("_", " ").split("|")[0] if disease else None
            result.clinvar_id = cols[2] if cols[2] != "." else None
            result.matched = True
            break

        # No ClinVar hit: still attach a dbSNP rsID if we have one.
        if not result.matched and not result.variant and dbsnp_rsid:
            result.variant = dbsnp_rsid

        gnomad_global, gnomad_sas = gnomad_freqs
        onekg_global, onekg_sas = onekg_freqs
        result.population = population.build_context(gnomad_global, gnomad_sas, onekg_global, onekg_sas)
        if result.population is not None:
            result.global_freq = result.population.global_freq
            result.south_asian_freq = result.population.south_asian_freq

        result.acmg_classification, result.acmg_basis, result.acmg_evidence = acmg.classify(
            result.global_freq,
            result.south_asian_freq,
            gnomad_covered or onekg_covered,
            result.significance,
            result.review_status,
        )
        return result

    def annotate(self, q: VariantQuery) -> Annotation:
        chrom = _norm_chrom(q.chrom)
        clinvar_rows = self._query_region(chrom, q.pos)
        dbsnp_rsid = self.dbsnp.rsid_for(chrom, q.pos, q.ref, q.alt) if self.dbsnp else None
        gnomad_freqs = self.gnomad.frequencies(chrom, q.pos, q.ref, q.alt) if self.gnomad else (None, None)
        onekg_freqs = self.onekg.frequencies(chrom, q.pos, q.ref, q.alt) if self.onekg else (None, None)
        gnomad_cov = bool(self.gnomad and self.gnomad.available and self.gnomad.covers(chrom))
        onekg_cov = bool(self.onekg and self.onekg.available and self.onekg.covers(chrom))
        return self._assemble(q, chrom, clinvar_rows, gnomad_freqs, onekg_freqs, dbsnp_rsid, gnomad_cov, onekg_cov)

    def _bulk_clinvar(self, positions: set[tuple[str, int]]) -> dict[tuple[str, int], list[list[str]]]:
        from .tabix_util import bulk_tabix

        out: dict[tuple[str, int], list[list[str]]] = {}
        for cols in bulk_tabix(self.vcf_path, self.tabix_bin, positions):
            if len(cols) < 8:
                continue
            out.setdefault((cols[0], int(cols[1])), []).append(cols)
        return out

    def annotate_many(self, queries: list[VariantQuery]) -> list[Annotation]:
        """Batch annotation: one bulk tabix pass per reference instead of per-variant."""
        if not queries:
            return []
        positions = {(_norm_chrom(q.chrom), q.pos) for q in queries}
        clinvar_bulk = self._bulk_clinvar(positions)
        dbsnp_bulk = self.dbsnp.bulk_rsids(positions) if self.dbsnp else {}
        gnomad_bulk = self.gnomad.bulk_frequencies(positions) if self.gnomad else {}
        onekg_bulk = self.onekg.bulk_frequencies(positions) if self.onekg else {}

        results = []
        for q in queries:
            chrom = _norm_chrom(q.chrom)
            rows = clinvar_bulk.get((chrom, q.pos), [])
            dbsnp_rsid = _rsid_from_bulk(dbsnp_bulk, chrom, q.pos, q.ref, q.alt)
            gnomad_freqs = _freq_from_bulk(gnomad_bulk, chrom, q.pos, q.ref, q.alt)
            onekg_freqs = _freq_from_bulk(onekg_bulk, chrom, q.pos, q.ref, q.alt)
            gnomad_cov = bool(self.gnomad and self.gnomad.available and self.gnomad.covers(chrom))
            onekg_cov = bool(self.onekg and self.onekg.available and self.onekg.covers(chrom))
            results.append(
                self._assemble(q, chrom, rows, gnomad_freqs, onekg_freqs, dbsnp_rsid, gnomad_cov, onekg_cov)
            )
        return results


def _freq_from_bulk(bulk, chrom, pos, ref, alt) -> tuple:
    for rec_ref, rec_alt, af, sas in bulk.get((chrom, pos), []):
        if rec_ref == ref and alt in rec_alt.split(","):
            return (af, sas)
    return (None, None)


def _rsid_from_bulk(bulk, chrom, pos, ref, alt) -> str | None:
    for rec_ref, rec_alt, rsid in bulk.get((chrom, pos), []):
        if rec_ref == ref and alt in rec_alt.split(",") and rsid.startswith("rs"):
            return rsid
    return None
