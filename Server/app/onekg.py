"""1000 Genomes SAS (South Asian) allele-frequency lookups (Week 6).

The GRCh38 phased release carries per-superpopulation AFs in INFO; we read AF
(global) and SAS_AF (South Asian). Contigs are bare names ('22'). This is an
independent South-Asian frequency source that cross-checks gnomAD's AF_sas.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def _norm_chrom(chrom: str) -> str:
    return chrom.replace("chr", "")


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


class OneKGenomesSAS:
    """Wraps a tabix-indexed 1000G sites VCF for SAS allele frequencies."""

    COVERED_CONTIGS = {"22"}

    def __init__(self, vcf_path: Path | None, tabix_bin: str = "tabix"):
        self.vcf_path = Path(vcf_path) if vcf_path else None
        self.tabix_bin = tabix_bin

    @property
    def available(self) -> bool:
        if not self.vcf_path:
            return False
        index = self.vcf_path.with_suffix(self.vcf_path.suffix + ".tbi")
        return self.vcf_path.exists() and index.exists() and shutil.which(self.tabix_bin) is not None

    def covers(self, chrom: str) -> bool:
        return _norm_chrom(chrom) in self.COVERED_CONTIGS

    def frequencies(self, chrom: str, pos: int, ref: str, alt: str) -> tuple[float | None, float | None]:
        """Return (global_af, sas_af) for the matching allele, or (None, None)."""
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
            if alt not in rec_alt.split(","):
                continue
            info = _parse_info(info_str)
            return (_to_float(info.get("AF")), _to_float(info.get("SAS_AF")))
        return (None, None)
