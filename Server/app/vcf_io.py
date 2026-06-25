"""Stream-parse uploaded VCFs (plain or gzip/bgzip) into the bits each engine needs.

Large real-world VCFs (WGS can be many GB) must NOT be loaded whole into memory.
These parsers stream line-by-line from a binary file object, transparently
decompress gzip/bgzip, and — for the genotype path — keep only the positions the
caller asks for, so memory stays bounded regardless of file size.
"""

from __future__ import annotations

import gzip
from typing import IO, Iterator

from .models import VariantQuery

# (chrom, pos) with bare chromosome names (no 'chr').
PositionSet = set[tuple[str, int]]


def _zygosity_copies(cols: list[str]) -> tuple[int, bool]:
    """Derive alt-allele copies from the GT field. Returns (copies, had_gt).

    2 = homozygous alt, 1 = het / hemizygous / unknown. had_gt is False when no
    FORMAT/sample GT is present (caller assumes heterozygous)."""
    if len(cols) < 10 or "GT" not in cols[8].split(":"):
        return 1, False
    gt_index = cols[8].split(":").index("GT")
    sample = cols[9].split(":")
    if gt_index >= len(sample):
        return 1, False
    alleles = sample[gt_index].replace("|", "/").split("/")
    alt_copies = sum(1 for a in alleles if a not in (".", "0"))
    return (2 if alt_copies >= 2 else 1), True


def _iter_data_lines(file_obj: IO[bytes]) -> Iterator[str]:
    """Yield non-header VCF lines from a binary stream, gzip/bgzip-aware."""
    file_obj.seek(0)
    magic = file_obj.read(2)
    file_obj.seek(0)
    # Force read mode: the uploaded SpooledTemporaryFile is opened writable, and
    # GzipFile would otherwise infer write mode from it and fail on read.
    stream: IO[bytes] = gzip.GzipFile(fileobj=file_obj, mode="rb") if magic == b"\x1f\x8b" else file_obj
    for raw in stream:
        line = raw.decode("utf-8", "replace").rstrip("\n")
        if not line or line.startswith("#"):
            continue
        yield line


def parse_vcf_genotypes_stream(
    file_obj: IO[bytes],
    wanted_positions: PositionSet | None = None,
    wanted_rsids: set[str] | None = None,
    max_records: int = 2_000_000,
) -> tuple[dict[tuple[str, int, str, str], int], dict[str, tuple[str, str, int]], bool]:
    """Stream a VCF into genotype indexes + whether any GT was seen.

    Returns (genotypes, rsid_index, any_gt):
      - genotypes:  {(chrom, pos, ref, alt): copies}  — position-keyed
      - rsid_index: {rsid: (ref, alt, copies)}         — rsID-keyed fallback so
        matching survives a genome-build mismatch (positions differ, rsIDs don't)

    If either `wanted_positions` or `wanted_rsids` is given, only records matching
    one of them are retained — PGx/PRS scan arbitrarily large files cheaply.
    """
    genotypes: dict[tuple[str, int, str, str], int] = {}
    rsid_index: dict[str, tuple[str, str, int]] = {}
    any_gt = False
    filtering = wanted_positions is not None or wanted_rsids is not None
    for line in _iter_data_lines(file_obj):
        cols = line.split("\t")
        if len(cols) < 5:
            cols = line.split()
        if len(cols) < 5:
            continue
        chrom = cols[0].replace("chr", "")
        try:
            pos = int(cols[1])
        except ValueError:
            continue
        vid = cols[2]
        if filtering:
            keep = (wanted_positions is not None and (chrom, pos) in wanted_positions) or (
                wanted_rsids is not None and vid in wanted_rsids
            )
            if not keep:
                continue
        ref = cols[3]
        copies, had_gt = _zygosity_copies(cols)
        any_gt = any_gt or had_gt
        for single_alt in cols[4].split(","):
            if single_alt in (".", ""):
                continue
            genotypes[(chrom, pos, ref, single_alt)] = copies
            if vid.startswith("rs"):
                rsid_index[vid] = (ref, single_alt, copies)
            if len(genotypes) >= max_records:
                return genotypes, rsid_index, any_gt
    return genotypes, rsid_index, any_gt


def parse_vcf_text_stream(file_obj: IO[bytes], max_variants: int = 10_000) -> tuple[list[VariantQuery], bool]:
    """Stream a VCF into VariantQuery objects (for /annotate), gzip-aware.

    Returns (variants, truncated) where truncated is True if max_variants was hit.
    """
    variants: list[VariantQuery] = []
    for line in _iter_data_lines(file_obj):
        cols = line.split("\t")
        if len(cols) < 5:
            cols = line.split()
        if len(cols) < 5:
            continue
        chrom, pos, _id, ref, alt = cols[0], cols[1], cols[2], cols[3], cols[4]
        try:
            pos_int = int(pos)
        except ValueError:
            continue
        for single_alt in alt.split(","):
            if single_alt in (".", ""):
                continue
            variants.append(VariantQuery(chrom=chrom, pos=pos_int, ref=ref, alt=single_alt))
            if len(variants) >= max_variants:
                return variants, True
    return variants, False
