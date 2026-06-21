"""Parse an uploaded user VCF into VariantQuery objects.

Lightweight, dependency-free text parser so a plain (uncompressed) user.vcf can
be annotated without requiring a tabix index on the input.
"""

from __future__ import annotations

from .models import VariantQuery


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
