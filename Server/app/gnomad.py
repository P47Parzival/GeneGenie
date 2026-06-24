"""gnomAD population allele-frequency lookups against a tabix-indexed subset.

We use gnomAD v4.1 *exomes* (largest South-Asian cohort) so AF_sas is well
populated. gnomAD VCFs use 'chr'-prefixed contigs ('chr22') on GRCh38.

INFO fields of interest:
  - AF     : overall allele frequency
  - AF_sas : South-Asian allele frequency  <-- the India-specific differentiator
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def _norm_chrom(chrom: str) -> str:
    c = chrom.strip()
    if not c.lower().startswith("chr"):
        c = f"chr{c}"
    return c


def _parse_info(info: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for part in info.split(";"):
        if not part:
            continue
        key, _, value = part.partition("=")
        fields[key] = value if value else "true"
    return fields


def _to_float(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


class GnomadLookup:
    def __init__(self, vcf_path: Path | None, tabix_bin: str = "tabix"):
        self.vcf_path = Path(vcf_path) if vcf_path else None
        self.tabix_bin = tabix_bin

    # Chromosomes present in the loaded subset (currently chr22 only).
    COVERED_CONTIGS = {"22"}

    @property
    def available(self) -> bool:
        if not self.vcf_path:
            return False
        # gnomAD ships .bgz with a .tbi index alongside.
        index = self.vcf_path.with_suffix(self.vcf_path.suffix + ".tbi")
        return self.vcf_path.exists() and index.exists() and shutil.which(self.tabix_bin) is not None

    def covers(self, chrom: str) -> bool:
        """Whether the loaded gnomAD subset includes this chromosome."""
        return chrom.replace("chr", "") in self.COVERED_CONTIGS

    def frequencies(self, chrom: str, pos: int, ref: str, alt: str) -> tuple[float | None, float | None]:
        """Return (global_freq, south_asian_freq) for the matching allele, or (None, None)."""
        if not self.available:
            return (None, None)

        region = f"{_norm_chrom(chrom)}:{pos}-{pos}"
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
            if len(cols) < 8:
                continue
            rec_pos, rec_ref, rec_alt, info_str = cols[1], cols[3], cols[4], cols[7]
            if int(rec_pos) != pos or rec_ref != ref:
                continue
            # gnomAD sites rows are decomposed to one ALT each, but be tolerant.
            alts = rec_alt.split(",")
            if alt not in alts:
                continue
            info = _parse_info(info_str)
            return (_to_float(info.get("AF")), _to_float(info.get("AF_sas")))
        return (None, None)
