"""Pharmacogenomics engine (Week 8): genotype -> diplotype -> phenotype -> drug.

Honest simplifications (documented in pgx_data.py): unphased genotypes, reference
(*1) assumed where a defining variant is absent, no CNV/structural alleles.
"""

from __future__ import annotations

from .models import PgxDrugGuidance, PgxGeneResult, PgxReport
from .pgx_data import DECREASED, DRUG_GUIDANCE, GENES, INCREASED, NO_FUNCTION, NORMAL

# patient genotypes: {(chrom, pos, ref, alt): copies(1|2)}
Genotypes = dict[tuple[str, int, str, str], int]


def _norm_chrom(chrom: str) -> str:
    return chrom.replace("chr", "")


def _allele_copies(allele: dict, genotypes: Genotypes, used: set) -> int:
    """Copies of this allele present: min zygosity across its defining variants.
    Returns 0 if any defining variant is absent. Marks consumed variant keys."""
    copies = 2
    keys = []
    for chrom, pos, ref, alt, _rs in allele["variants"]:
        key = (_norm_chrom(chrom), pos, ref, alt)
        if key in used or key not in genotypes:
            return 0
        copies = min(copies, genotypes[key])
        keys.append(key)
    used.update(keys)
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


def _call_gene(gene: str, gene_def: dict, genotypes: Genotypes) -> PgxGeneResult:
    used: set = set()
    detected: list[tuple[str, str, int]] = []  # (name, function, copies)
    for allele in gene_def["alleles"]:
        copies = _allele_copies(allele, genotypes, used)
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


def run_pgx(genotypes: Genotypes, genotypes_have_zygosity: bool) -> PgxReport:
    results = [_call_gene(gene, gene_def, genotypes) for gene, gene_def in GENES.items()]
    note = (
        "MVP pharmacogenomics over a curated CPIC subset (CYP2C19, TPMT, DPYD, SLCO1B1). "
        "Star alleles assume unphased genotypes; reference (*1) is assumed where a defining "
        "variant is absent. Not a substitute for clinical PGx testing."
    )
    if not genotypes_have_zygosity:
        note += " No GT/zygosity in input — heterozygous assumed for detected variants."
    return PgxReport(genes_tested=list(GENES.keys()), results=results, note=note)
