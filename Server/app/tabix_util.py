"""Bulk tabix query: fetch all records at many positions in ONE process.

Per-variant tabix calls (one subprocess each) don't scale to thousands of
variants. `tabix -R <bed>` does a single index-backed pass over a region file,
turning N subprocess spawns into one. Used by the batch annotation path.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from typing import Iterable


def bulk_tabix(vcf_path, tabix_bin: str, regions: Iterable[tuple[str, int]]) -> list[list[str]]:
    """Return split VCF columns for every record at the given positions.

    `regions` are (contig, pos) pairs in the TARGET FILE's own contig naming
    (e.g. 'chr22' for gnomAD, 'NC_000022.11' for dbSNP). pos is 1-based.
    """
    region_list = sorted(set(regions))
    if not region_list:
        return []
    fd, bed_path = tempfile.mkstemp(suffix=".bed")
    try:
        with os.fdopen(fd, "w") as bed:
            for contig, pos in region_list:
                bed.write(f"{contig}\t{pos - 1}\t{pos}\n")  # BED is 0-based half-open
        proc = subprocess.run(
            [tabix_bin, "-R", bed_path, str(vcf_path)],
            capture_output=True,
            text=True,
            check=True,
        )
    finally:
        os.unlink(bed_path)
    return [ln.split("\t") for ln in proc.stdout.splitlines() if ln and not ln.startswith("#")]
