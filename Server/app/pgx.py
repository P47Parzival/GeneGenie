"""Pharmacogenomics engine (Week 8): genotype -> diplotype -> phenotype -> drug.

Honest simplifications (documented in pgx_data.py): unphased genotypes, reference
(*1) assumed where a defining variant is absent, no CNV/structural alleles.
"""

from __future__ import annotations

from .models import PgxDrugGuidance, PgxGeneResult, PgxReport
from .pgx_data import CYP2D6_ACTIVITY, DECREASED, DRUG_GUIDANCE, GENES, INCREASED, NO_FUNCTION, NORMAL

# patient genotypes: {(chrom, pos, ref, alt): copies(1|2)}
Genotypes = dict[tuple[str, int, str, str], int]


def _norm_chrom(chrom: str) -> str:
    return chrom.replace("chr", "")


def defining_positions() -> set[tuple[str, int]]:
    """All (chrom, pos) sites that define any PGx star allele — for VCF prefiltering."""
    positions: set[tuple[str, int]] = set()
    for gene_def in GENES.values():
        for allele in gene_def["alleles"]:
            for chrom, pos, _ref, _alt, _rs in allele["variants"]:
                positions.add((_norm_chrom(chrom), pos))
    return positions


def defining_rsids() -> set[str]:
    """All rsIDs defining any PGx star allele — rsID fallback survives build mismatch."""
    rsids: set[str] = set()
    for gene_def in GENES.values():
        for allele in gene_def["alleles"]:
            for _chrom, _pos, _ref, _alt, rs in allele["variants"]:
                if rs:
                    rsids.add(rs)
    return rsids


def _lookup_copies(chrom, pos, ref, alt, rs, genotypes: Genotypes, rsid_index) -> int | None:
    """Alt-allele copies at this variant, by position then rsID. None if absent."""
    key = (_norm_chrom(chrom), pos, ref, alt)
    if key in genotypes:
        return genotypes[key]
    rec = rsid_index.get(rs)  # (ref, alt, copies)
    if rec and rec[1] == alt:
        return rec[2]
    return None


def _allele_copies(allele: dict, genotypes: Genotypes, rsid_index, used: set) -> int:
    """Copies of this allele present: min zygosity across its defining variants.
    Returns 0 if any defining variant is absent. Marks consumed variants (by rsID)."""
    copies = 2
    seen = []
    for chrom, pos, ref, alt, rs in allele["variants"]:
        marker = rs or f"{chrom}:{pos}:{alt}"
        if marker in used:
            return 0
        c = _lookup_copies(chrom, pos, ref, alt, rs, genotypes, rsid_index)
        if c is None:
            return 0
        copies = min(copies, c)
        seen.append(marker)
    used.update(seen)
    return copies


def _phenotype(gene: str, functions: list[str]) -> str:
    """Map the two haplotype functions to a CPIC phenotype label."""
    nf = functions.count(NO_FUNCTION)
    dec = functions.count(DECREASED)
    inc = functions.count(INCREASED)

    if gene == "CYP2C19":
        if inc == 2:
            return "Ultrarapid Metabolizer"
        if inc == 1 and nf == 0:
            return "Rapid Metabolizer"
        if nf == 2:
            return "Poor Metabolizer"
        if nf == 1:
            return "Intermediate Metabolizer"
        return "Normal Metabolizer"

    if gene == "TPMT":
        if nf == 2:
            return "Poor Metabolizer"
        if nf == 1:
            return "Intermediate Metabolizer"
        return "Normal Metabolizer"

    if gene == "DPYD":
        score = sum(1.0 if f == NORMAL else 0.5 if f == DECREASED else 0.0 for f in functions)
        if score >= 2:
            return "Normal Metabolizer"
        if score >= 1:
            return "Intermediate Metabolizer"
        return "Poor Metabolizer"

    if gene == "SLCO1B1":
        if dec == 2:
            return "Poor Function"
        if dec == 1:
            return "Decreased Function"
        return "Normal Function"

    return "Normal Metabolizer"


def _call_gene(gene: str, gene_def: dict, genotypes: Genotypes, rsid_index) -> PgxGeneResult:
    used: set = set()
    detected: list[tuple[str, str, int]] = []  # (name, function, copies)
    for allele in gene_def["alleles"]:
        copies = _allele_copies(allele, genotypes, rsid_index, used)
        if copies > 0:
            detected.append((allele["name"], allele["function"], copies))

    # Fill two haplotype slots; default reference (*1, normal function).
    slots: list[tuple[str, str]] = []  # (name, function)
    for name, func, copies in detected:
        for _ in range(copies):
            if len(slots) < 2:
                slots.append((name, func))
    while len(slots) < 2:
        slots.append(("*1", NORMAL))

    # Diplotype string in conventional notation: reference (*1) first.
    names = sorted((s[0] for s in slots), key=lambda n: (n != "*1", n))
    diplotype = "/".join(names)
    phenotype = _phenotype(gene, [s[1] for s in slots])

    guidance = DRUG_GUIDANCE.get(gene, {}).get(phenotype, [])
    drugs = [PgxDrugGuidance(drug=g["drug"], recommendation=g["recommendation"]) for g in guidance]

    detected_labels = [f"{name} (x{copies})" for name, _f, copies in detected]
    return PgxGeneResult(
        gene=gene,
        diplotype=diplotype,
        phenotype=phenotype,
        detected=detected_labels,
        drugs=drugs,
    )


def _observed_sites(genotypes: Genotypes, rsid_index) -> tuple[int, int]:
    seen: set = set()
    total: set = set()
    for gene_def in GENES.values():
        for allele in gene_def["alleles"]:
            for chrom, pos, ref, alt, rs in allele["variants"]:
                marker = rs or f"{chrom}:{pos}:{alt}"
                total.add(marker)
                if _lookup_copies(chrom, pos, ref, alt, rs, genotypes, rsid_index) is not None:
                    seen.add(marker)
    return len(seen), len(total)


def _cyp2d6_phenotype(score: float) -> str:
    if score == 0:
        return "Poor Metabolizer"
    if score < 1.25:
        return "Intermediate Metabolizer"
    if score <= 2.25:
        return "Normal Metabolizer"
    return "Ultrarapid Metabolizer"


def _call_cyp2d6(gene_def: dict, genotypes: Genotypes, rsid_index) -> PgxGeneResult:
    """Dedicated CYP2D6 caller: handles the *10-on-*4 linkage and uses CPIC
    activity scores. SNV-based only — CNV/hybrid alleles are not detected."""
    def count(rs, chrom, pos, ref, alt) -> int:
        return _lookup_copies(chrom, pos, ref, alt, rs, genotypes, rsid_index) or 0

    c4 = count("rs3892097", "22", 42128945, "C", "T")
    c10_raw = count("rs1065852", "22", 42130692, "G", "A")
    c41 = count("rs28371725", "22", 42127803, "C", "T")
    c10 = max(0, c10_raw - c4)  # rs1065852 also rides on *4; remove those copies

    # Materialise detected non-reference alleles, most impactful (lowest activity) first.
    alleles: list[str] = ["*4"] * c4 + ["*10"] * c10 + ["*41"] * c41
    alleles.sort(key=lambda name: CYP2D6_ACTIVITY[name])
    slots = alleles[:2] + ["*1"] * max(0, 2 - len(alleles))

    score = sum(CYP2D6_ACTIVITY[name] for name in slots)
    phenotype = _cyp2d6_phenotype(score)
    diplotype = "/".join(sorted(slots, key=lambda n: (n != "*1", n)))

    detected = []
    for name, n in (("*4", c4), ("*10", c10), ("*41", c41)):
        if n:
            detected.append(f"{name} (x{n})")

    guidance = DRUG_GUIDANCE.get("CYP2D6", {}).get(phenotype, [])
    drugs = [PgxDrugGuidance(drug=g["drug"], recommendation=g["recommendation"]) for g in guidance]
    return PgxGeneResult(
        gene="CYP2D6",
        diplotype=f"{diplotype} (AS {score:g})",
        phenotype=phenotype,
        detected=detected,
        drugs=drugs,
    )


def run_pgx(genotypes: Genotypes, rsid_index, genotypes_have_zygosity: bool) -> PgxReport:
    results = []
    for gene, gene_def in GENES.items():
        if gene == "CYP2D6":
            results.append(_call_cyp2d6(gene_def, genotypes, rsid_index))
        else:
            results.append(_call_gene(gene, gene_def, genotypes, rsid_index))
    sites_observed, sites_total = _observed_sites(genotypes, rsid_index)

    note = (
        "MVP pharmacogenomics over a curated CPIC subset (CYP2C19, TPMT, DPYD, SLCO1B1, CYP2D6). "
        "Star alleles assume unphased genotypes; reference (*1) is assumed where a defining "
        "variant is absent. CYP2D6 is SNV-based only — gene deletions (*5), duplications, and "
        "hybrid alleles are NOT detected, so its result is approximate. "
        "Not a substitute for clinical PGx testing."
    )
    if sites_observed == 0:
        note = (
            "WARNING: none of the PGx defining variants were found in this VCF — likely a "
            "genome-build mismatch (this engine uses GRCh38) or the file does not cover these "
            "sites. Every gene defaulted to *1/*1, which is NOT an informative result. " + note
        )
    if not genotypes_have_zygosity:
        note += " No GT/zygosity in input — heterozygous assumed for detected variants."
    return PgxReport(
        genes_tested=list(GENES.keys()),
        results=results,
        note=note,
        sites_observed=sites_observed,
        sites_total=sites_total,
    )
