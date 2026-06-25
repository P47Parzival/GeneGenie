"""gnomAD population allele-frequency lookups against a tabix-indexed subset.

We use gnomAD v4.1 *exomes* (largest South-Asian cohort) so AF_sas is well
populated. gnomAD VCFs use 'chr'-prefixed contigs ('chr22') on GRCh38.

INFO fields of interest:
  - AF     : overall allele frequency
  - AF_sas : South-Asian allele frequency  <-- the India-specific differentiator
"""

from __future__ import annotations

import subprocess


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
    def __init__(self, dataset, tabix_bin: str = "tabix"):
        self.dataset = dataset
        self.vcf_path = dataset.local_path if dataset else None
        self.tabix_bin = tabix_bin

    @property
    def available(self) -> bool:
        return bool(self.dataset and self.dataset.available())

    def covers(self, chrom: str) -> bool:
        """Whether the loaded gnomAD subset includes this chromosome."""
        return bool(self.dataset and self.dataset.covers(chrom))

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

    def bulk_frequencies(self, positions) -> dict[tuple[str, int], list[tuple[str, str, float | None, float | None]]]:
        """One-pass lookup for many (bare_chrom, pos) -> [(ref, alt, AF, AF_sas)]."""
        from .tabix_util import bulk_tabix

        if not self.available:
            return {}
        regions = [(_norm_chrom(c), p) for (c, p) in positions if self.covers(c)]
        out: dict[tuple[str, int], list] = {}
        for cols in bulk_tabix(self.vcf_path, self.tabix_bin, regions):
            if len(cols) < 8:
                continue
            bare = cols[0].replace("chr", "")
            info = _parse_info(cols[7])
            out.setdefault((bare, int(cols[1])), []).append(
                (cols[3], cols[4], _to_float(info.get("AF")), _to_float(info.get("AF_sas")))
            )
        return out
