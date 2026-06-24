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

    def annotate(self, q: VariantQuery) -> Annotation:
        chrom = _norm_chrom(q.chrom)
        result = Annotation(chrom=chrom, pos=q.pos, ref=q.ref, alt=q.alt)

        for cols in self._query_region(chrom, q.pos):
            # VCF: CHROM POS ID REF ALT QUAL FILTER INFO
            if len(cols) < 8:
                continue
            rec_pos, rec_id, rec_ref, rec_alt, info_str = cols[1], cols[2], cols[3], cols[4], cols[7]
            if int(rec_pos) != q.pos or rec_ref != q.ref:
                continue
            if q.alt not in rec_alt.split(","):
                continue

            info = _parse_info(info_str)
            geneinfo = info.get("GENEINFO")
            rs = info.get("RS")
            disease = info.get("CLNDN")

            result.gene = geneinfo.split(":")[0] if geneinfo else None
            result.variant = f"rs{rs}" if rs else None
            result.significance = info.get("CLNSIG")
            result.review_status = info.get("CLNREVSTAT")
            result.disease = disease.replace("_", " ").split("|")[0] if disease else None
            result.clinvar_id = rec_id if rec_id != "." else None
            result.matched = True
            break

        # No ClinVar hit: still try to attach a dbSNP rsID if we have the subset.
        if not result.matched and not result.variant and self.dbsnp is not None:
            result.variant = self.dbsnp.rsid_for(chrom, q.pos, q.ref, q.alt)

        # Population frequencies: gnomAD (AF, AF_sas) + 1000G (AF, SAS_AF).
        gnomad_global = gnomad_sas = onekg_global = onekg_sas = None
        covered = False
        if self.gnomad is not None:
            gnomad_global, gnomad_sas = self.gnomad.frequencies(chrom, q.pos, q.ref, q.alt)
            covered = covered or (self.gnomad.available and self.gnomad.covers(chrom))
        if self.onekg is not None:
            onekg_global, onekg_sas = self.onekg.frequencies(chrom, q.pos, q.ref, q.alt)
            covered = covered or (self.onekg.available and self.onekg.covers(chrom))

        # Build the Indian-population context and set combined headline frequencies.
        result.population = population.build_context(gnomad_global, gnomad_sas, onekg_global, onekg_sas)
        if result.population is not None:
            result.global_freq = result.population.global_freq
            result.south_asian_freq = result.population.south_asian_freq

        # ACMG classification from the evidence we can power (population AF + ClinVar).
        result.acmg_classification, result.acmg_basis, result.acmg_evidence = acmg.classify(
            result.global_freq,
            result.south_asian_freq,
            covered,
            result.significance,
            result.review_status,
        )

        return result

    def annotate_many(self, queries: list[VariantQuery]) -> list[Annotation]:
        return [self.annotate(q) for q in queries]
