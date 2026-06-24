"""Pharmacogenomics knowledge base (Week 8) — curated, verified subset.

GRCh38 coordinates and forward-strand REF/ALT verified via Ensembl REST
(rest.ensembl.org/variation/human/<rsid>). Functional assignments and drug
guidance follow CPIC. This is an HONEST MVP subset of high-value, largely
SNV-callable pharmacogenes — NOT a complete star-allele caller.

Out of scope here (documented, deferred): CYP2D6 (copy-number + many alleles),
warfarin dosing (CYP2C9 + VKORC1 algorithm), structural/CNV alleles, phasing.
Star-allele calls assume unphased genotypes and reference (*1) where a defining
variant is absent — the standard simplification for a targeted panel.
"""

from __future__ import annotations

# Functional statuses
NO_FUNCTION = "no_function"
DECREASED = "decreased_function"
NORMAL = "normal_function"
INCREASED = "increased_function"

# Each allele: name, function, and the defining variant(s) as
# (chrom, pos, ref, alt, rsid). Composite alleles (e.g. TPMT*3A) list multiple
# variants and MUST be ordered before their component alleles for correct calling.
GENES: dict[str, dict] = {
    "CYP2C19": {
        "chrom": "10",
        "alleles": [
            {"name": "*17", "function": INCREASED, "variants": [("10", 94761900, "C", "T", "rs12248560")]},
            {"name": "*2", "function": NO_FUNCTION, "variants": [("10", 94781859, "G", "A", "rs4244285")]},
            {"name": "*3", "function": NO_FUNCTION, "variants": [("10", 94780653, "G", "A", "rs4986893")]},
        ],
    },
    "TPMT": {
        "chrom": "6",
        "alleles": [
            # *3A = *3B (rs1800460) + *3C (rs1142345) in cis; match before components.
            {"name": "*3A", "function": NO_FUNCTION, "variants": [
                ("6", 18138997, "C", "T", "rs1800460"),
                ("6", 18130687, "T", "C", "rs1142345"),
            ]},
            {"name": "*3B", "function": NO_FUNCTION, "variants": [("6", 18138997, "C", "T", "rs1800460")]},
            {"name": "*3C", "function": NO_FUNCTION, "variants": [("6", 18130687, "T", "C", "rs1142345")]},
            {"name": "*2", "function": NO_FUNCTION, "variants": [("6", 18143724, "C", "G", "rs1800462")]},
        ],
    },
    "DPYD": {
        "chrom": "1",
        "alleles": [
            {"name": "*2A", "function": NO_FUNCTION, "variants": [("1", 97450058, "C", "T", "rs3918290")]},
            {"name": "c.2846A>T", "function": DECREASED, "variants": [("1", 97082391, "T", "A", "rs67376798")]},
        ],
    },
    "SLCO1B1": {
        "chrom": "12",
        "alleles": [
            {"name": "*5", "function": DECREASED, "variants": [("12", 21178615, "T", "C", "rs4149056")]},
        ],
    },
}


# Phenotype -> drug guidance (CPIC). Keyed by gene then phenotype label.
DRUG_GUIDANCE: dict[str, dict[str, list[dict]]] = {
    "CYP2C19": {
        "Poor Metabolizer": [{"drug": "clopidogrel", "recommendation":
            "Markedly reduced platelet inhibition and higher risk of cardiovascular events. "
            "Avoid clopidogrel; use prasugrel or ticagrelor if not contraindicated."}],
        "Intermediate Metabolizer": [{"drug": "clopidogrel", "recommendation":
            "Reduced clopidogrel activation and efficacy. Consider prasugrel or ticagrelor."}],
        "Normal Metabolizer": [{"drug": "clopidogrel", "recommendation": "Standard clopidogrel dosing."}],
        "Rapid Metabolizer": [{"drug": "clopidogrel", "recommendation": "Standard clopidogrel dosing."}],
        "Ultrarapid Metabolizer": [{"drug": "clopidogrel", "recommendation": "Standard clopidogrel dosing."}],
    },
    "TPMT": {
        "Poor Metabolizer": [{"drug": "azathioprine / mercaptopurine", "recommendation":
            "Very high risk of severe myelosuppression. Drastically reduce dose (e.g. ~10x) and adjust by tolerance, "
            "or select an alternative agent."}],
        "Intermediate Metabolizer": [{"drug": "azathioprine / mercaptopurine", "recommendation":
            "Start with a reduced dose (30–80% of target) and titrate by tolerance."}],
        "Normal Metabolizer": [{"drug": "azathioprine / mercaptopurine", "recommendation": "Standard dosing."}],
    },
    "DPYD": {
        "Poor Metabolizer": [{"drug": "fluorouracil / capecitabine", "recommendation":
            "High risk of severe, potentially fatal toxicity. Avoid fluoropyrimidines; select an alternative."}],
        "Intermediate Metabolizer": [{"drug": "fluorouracil / capecitabine", "recommendation":
            "Reduce starting dose by 50% and titrate by toxicity / exposure."}],
        "Normal Metabolizer": [{"drug": "fluorouracil / capecitabine", "recommendation": "Standard dosing."}],
    },
    "SLCO1B1": {
        "Poor Function": [{"drug": "simvastatin", "recommendation":
            "High risk of statin-associated myopathy. Use a lower dose or an alternative statin; consider routine CK monitoring."}],
        "Decreased Function": [{"drug": "simvastatin", "recommendation":
            "Increased myopathy risk. Consider a lower dose or alternative statin."}],
        "Normal Function": [{"drug": "simvastatin", "recommendation": "Standard simvastatin dosing."}],
    },
}
