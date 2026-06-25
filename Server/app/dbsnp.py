"""dbSNP rsID lookups against a tabix-indexed dbSNP subset (e.g. chr22).

dbSNP VCFs use RefSeq accessions (NC_000022.11) rather than '22'. We map common
GRCh38 chromosome names to their RefSeq accession so a normal {chrom,pos} query
resolves. Only the subset chromosomes we actually downloaded will resolve.
"""

from __future__ import annotations

import subprocess

# GRCh38 primary assembly RefSeq accessions (extend as more dbSNP subsets land).
GRCH38_REFSEQ: dict[str, str] = {
    "22": "NC_000022.11",
}


class DbSnpLookup:
    def __init__(self, dataset, tabix_bin: str = "tabix"):
        self.dataset = dataset
        self.vcf_path = dataset.local_path if dataset else None
        self.tabix_bin = tabix_bin

    @property
    def available(self) -> bool:
        return bool(self.dataset and self.dataset.available())

    def rsid_for(self, chrom: str, pos: int, ref: str, alt: str) -> str | None:
        if not self.available:
            return None
        accession = GRCH38_REFSEQ.get(chrom.replace("chr", ""))
        if not accession:
            return None

        region = f"{accession}:{pos}-{pos}"
        proc = subprocess.run(
            [self.tabix_bin, str(self.vcf_path), region],
            capture_output=True,
            text=True,
            check=True,
        )
        for line in proc.stdout.splitlines():
            if not line or line.startswith("#"):
                continue
            cols = line.split("\t")
            if len(cols) < 5:
                continue
            rec_pos, rec_id, rec_ref, rec_alt = cols[1], cols[2], cols[3], cols[4]
            if int(rec_pos) != pos or rec_ref != ref:
                continue
            if alt not in rec_alt.split(","):
                continue
            return rec_id if rec_id.startswith("rs") else None
        return None

    def bulk_rsids(self, positions) -> dict[tuple[str, int], list[tuple[str, str, str]]]:
        """One-pass lookup for many (bare_chrom, pos) -> [(ref, alt, rsid)]."""
        from .tabix_util import bulk_tabix

        if not self.available:
            return {}
        acc_to_bare: dict[str, str] = {}
        regions = []
        for chrom, pos in positions:
            bare = chrom.replace("chr", "")
            accession = GRCH38_REFSEQ.get(bare)
            if accession:
                acc_to_bare[accession] = bare
                regions.append((accession, pos))
        out: dict[tuple[str, int], list] = {}
        for cols in bulk_tabix(self.vcf_path, self.tabix_bin, regions):
            if len(cols) < 5:
                continue
            bare = acc_to_bare.get(cols[0], cols[0])
            out.setdefault((bare, int(cols[1])), []).append((cols[3], cols[4], cols[2]))
        return out
