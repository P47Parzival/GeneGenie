"""Polygenic risk score models (Week 5) — curated, illustrative.

IMPORTANT — honesty: this is an ILLUSTRATIVE / educational model, not a clinically
validated PGS. Effect weights are ln(odds ratio) from well-established published
T2D GWAS hits (approximate). GRCh38 positions, alleles, and 1000 Genomes SAS
effect-allele frequencies were verified via the Ensembl REST API.

Percentiles are computed against a South-Asian reference distribution derived
analytically from these SAS allele frequencies (Hardy-Weinberg + linkage
equilibrium normal approximation), NOT a European-derived reference — this is the
ancestry-aware angle. The LE assumption ignores LD between SNPs and so the
variance (hence the spread of percentiles) is approximate.
"""

from __future__ import annotations

import math


def _w(odds_ratio: float) -> float:
    return round(math.log(odds_ratio), 5)


# Each variant: rsid, chrom, pos (GRCh38), ref (assembly reference allele),
# effect_allele (risk), weight (ln OR), sas_eaf (1000G SAS effect-allele freq).
T2D_VARIANTS = [
    {"rsid": "rs7903146",  "gene": "TCF7L2",   "chrom": "10", "pos": 112998590, "ref": "C", "effect_allele": "T", "weight": _w(1.40), "sas_eaf": 0.299},
    {"rsid": "rs10811661", "gene": "CDKN2A/B", "chrom": "9",  "pos": 22134095,  "ref": "T", "effect_allele": "T", "weight": _w(1.20), "sas_eaf": 0.868},
    {"rsid": "rs9939609",  "gene": "FTO",      "chrom": "16", "pos": 53786615,  "ref": "T", "effect_allele": "A", "weight": _w(1.15), "sas_eaf": 0.288},
    {"rsid": "rs5219",     "gene": "KCNJ11",   "chrom": "11", "pos": 17388025,  "ref": "T", "effect_allele": "T", "weight": _w(1.14), "sas_eaf": 0.396},
    {"rsid": "rs13266634", "gene": "SLC30A8",  "chrom": "8",  "pos": 117172544, "ref": "C", "effect_allele": "C", "weight": _w(1.12), "sas_eaf": 0.745},
    {"rsid": "rs1801282",  "gene": "PPARG",    "chrom": "3",  "pos": 12351626,  "ref": "C", "effect_allele": "C", "weight": _w(1.14), "sas_eaf": 0.880},
    {"rsid": "rs7754840",  "gene": "CDKAL1",   "chrom": "6",  "pos": 20661019,  "ref": "G", "effect_allele": "C", "weight": _w(1.12), "sas_eaf": 0.256},
    {"rsid": "rs1111875",  "gene": "HHEX",     "chrom": "10", "pos": 92703125,  "ref": "C", "effect_allele": "C", "weight": _w(1.13), "sas_eaf": 0.356},
    {"rsid": "rs4402960",  "gene": "IGF2BP2",  "chrom": "3",  "pos": 185793899, "ref": "G", "effect_allele": "T", "weight": _w(1.14), "sas_eaf": 0.455},
    {"rsid": "rs2237892",  "gene": "KCNQ1",    "chrom": "11", "pos": 2818521,   "ref": "C", "effect_allele": "C", "weight": _w(1.40), "sas_eaf": 0.986},
]

MODELS = [
    {
        "id": "T2D_illustrative_v1",
        "trait": "Type 2 Diabetes",
        "ancestry": "South Asian (1000G SAS)",
        "description": "Illustrative 10-variant T2D model from established GWAS loci. "
                       "Educational only — not a clinically validated polygenic score.",
        "variants": T2D_VARIANTS,
    },
]
