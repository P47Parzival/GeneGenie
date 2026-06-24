"""Parse an uploaded user VCF into VariantQuery objects.

Lightweight, dependency-free text parser so a plain (uncompressed) user.vcf can
be annotated without requiring a tabix index on the input.
"""

from __future__ import annotations

from .models import VariantQuery


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


def parse_vcf_genotypes(text: str, max_records: int = 50_000) -> tuple[dict[tuple[str, int, str, str], int], bool]:
    """Parse a VCF into {(chrom, pos, ref, alt): copies} plus whether any GT was seen.

    Used by the PGx engine, which needs zygosity. Chromosomes are normalized to
    bare names (no 'chr')."""
    genotypes: dict[tuple[str, int, str, str], int] = {}
    any_gt = False
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
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
        ref = cols[3]
        copies, had_gt = _zygosity_copies(cols)
        any_gt = any_gt or had_gt
        for single_alt in cols[4].split(","):
            if single_alt in (".", ""):
                continue
            genotypes[(chrom, pos, ref, single_alt)] = copies
            if len(genotypes) >= max_records:
                return genotypes, any_gt
    return genotypes, any_gt


def parse_vcf_text(text: str, max_variants: int = 10_000) -> list[VariantQuery]:
    variants: list[VariantQuery] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        cols = line.split("\t")
        if len(cols) < 5:
            cols = line.split()  # tolerate space-delimited
        if len(cols) < 5:
            continue
        chrom, pos, _id, ref, alt = cols[0], cols[1], cols[2], cols[3], cols[4]
        try:
            pos_int = int(pos)
        except ValueError:
            continue
        # A record may carry multiple comma-separated ALT alleles.
        for single_alt in alt.split(","):
            if single_alt in (".", ""):
                continue
            variants.append(VariantQuery(chrom=chrom, pos=pos_int, ref=ref, alt=single_alt))
            if len(variants) >= max_variants:
                return variants
    return variants
