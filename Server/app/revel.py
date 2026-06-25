"""REVEL in-silico missense pathogenicity scores (predictor layer).

REVEL is an ensemble missense predictor (0-1, higher = more likely pathogenic).
We use the ClinGen SVI-calibrated thresholds (Pejaver et al. 2022) to assign
ACMG PP3 / BP4 at the appropriate strength. Only missense variants are scored.

Tabix-indexed TSV columns: chrom, pos, ref, alt, REVEL.
"""

from __future__ import annotations

import subprocess


class RevelLookup:
    def __init__(self, dataset, tabix_bin: str = "tabix"):
        self.dataset = dataset
        self.path = dataset.local_path if dataset else None
        self.tabix_bin = tabix_bin

    @property
    def available(self) -> bool:
        return bool(self.dataset and self.dataset.available())

    def covers(self, chrom: str) -> bool:
        return bool(self.dataset and self.dataset.covers(chrom))

    def score(self, chrom: str, pos: int, ref: str, alt: str) -> float | None:
        if not self.available:
            return None
        c = chrom.replace("chr", "")
        proc = subprocess.run(
            [self.tabix_bin, str(self.path), f"{c}:{pos}-{pos}"],
            capture_output=True,
            text=True,
            check=True,
        )
        for line in proc.stdout.splitlines():
            cols = line.split("\t")
            if len(cols) < 5:
                continue
            if cols[2] == ref and cols[3] == alt:
                try:
                    return float(cols[4])
                except ValueError:
                    return None
        return None

    def bulk_scores(self, positions) -> dict[tuple[str, int], list[tuple[str, str, float]]]:
        """One-pass lookup for many (bare_chrom, pos) -> [(ref, alt, REVEL)]."""
        from .tabix_util import bulk_tabix

        if not self.available:
            return {}
        regions = [(c.replace("chr", ""), p) for (c, p) in positions if self.covers(c)]
        out: dict[tuple[str, int], list] = {}
        for cols in bulk_tabix(self.path, self.tabix_bin, regions):
            if len(cols) < 5:
                continue
            try:
                sc = float(cols[4])
            except ValueError:
                continue
            out.setdefault((cols[0], int(cols[1])), []).append((cols[2], cols[3], sc))
        return out
