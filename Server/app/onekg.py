"""1000 Genomes SAS (South Asian) allele-frequency lookups (Week 6).

The GRCh38 phased release carries per-superpopulation AFs in INFO; we read AF
(global) and SAS_AF (South Asian). Contigs are bare names ('22'). This is an
independent South-Asian frequency source that cross-checks gnomAD's AF_sas.
"""

from __future__ import annotations

import subprocess


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

    def __init__(self, dataset, tabix_bin: str = "tabix"):
        self.dataset = dataset
        self.vcf_path = dataset.local_path if dataset else None
        self.tabix_bin = tabix_bin

    @property
    def available(self) -> bool:
        return bool(self.dataset and self.dataset.available())

    def covers(self, chrom: str) -> bool:
        return bool(self.dataset and self.dataset.covers(chrom))

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

    def bulk_frequencies(self, positions) -> dict[tuple[str, int], list[tuple[str, str, float | None, float | None]]]:
        """One-pass lookup for many (bare_chrom, pos) -> [(ref, alt, AF, SAS_AF)]."""
        from .tabix_util import bulk_tabix

        if not self.available:
            return {}
        regions = [(_norm_chrom(c), p) for (c, p) in positions if self.covers(c)]
        out: dict[tuple[str, int], list] = {}
        for cols in bulk_tabix(self.vcf_path, self.tabix_bin, regions):
            if len(cols) < 8:
                continue
            info = _parse_info(cols[7])
            out.setdefault((cols[0].replace("chr", ""), int(cols[1])), []).append(
                (cols[3], cols[4], _to_float(info.get("AF")), _to_float(info.get("SAS_AF")))
            )
        return out
