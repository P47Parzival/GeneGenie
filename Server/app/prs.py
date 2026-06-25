"""Polygenic risk score engine (Week 5).

Pipeline: patient VCF -> effect-allele dosage per model variant -> weighted sum
-> z-score vs a South-Asian reference distribution (analytic HWE+LE) -> percentile.

Honest limitations (surfaced in the response note):
  - Illustrative model, not a clinical PGS (see prs_data.py).
  - LE approximation ignores LD, so the reference variance is approximate.
  - Absence of a variant record is treated as homozygous reference (standard for
    a complete call-set; a targeted VCF that simply lacks the site is reported via
    the `variants_observed` coverage count).
"""

from __future__ import annotations

import math

from .models import PrsResponse, PrsTraitResult
from .prs_data import MODELS

# patient index: (chrom, pos) -> (ref, alt, alt_copies)
PosIndex = dict[tuple[str, int], tuple[str, str, int]]


def _norm(chrom: str) -> str:
    return chrom.replace("chr", "")


def model_positions() -> set[tuple[str, int]]:
    """All (chrom, pos) sites used by any PRS model — for VCF prefiltering."""
    positions: set[tuple[str, int]] = set()
    for model in MODELS:
        for v in model["variants"]:
            positions.add((_norm(v["chrom"]), v["pos"]))
    return positions


def model_rsids() -> set[str]:
    """All rsIDs used by any PRS model — rsID fallback survives build mismatch."""
    return {v["rsid"] for model in MODELS for v in model["variants"] if v.get("rsid")}


def _phi(z: float) -> float:
    """Standard normal CDF."""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def build_pos_index(genotypes: dict[tuple[str, int, str, str], int]) -> PosIndex:
    index: PosIndex = {}
    for (chrom, pos, ref, alt), copies in genotypes.items():
        index[(_norm(chrom), pos)] = (ref, alt, copies)
    return index


def _dosage(variant: dict, index: PosIndex, rsid_index: dict[str, tuple[str, str, int]]) -> tuple[int, bool]:
    """Effect-allele dosage (0..2) and whether the site was observed in the VCF.

    Matches by position first, then by rsID (so a genome-build mismatch — different
    coordinates, same rsID — still resolves)."""
    ea = variant["effect_allele"]
    ref = variant["ref"]
    rec = index.get((variant["chrom"], variant["pos"]))
    if rec is None:
        rec = rsid_index.get(variant.get("rsid", ""))
    if rec is None:
        # No record -> assume homozygous reference.
        return (2 if ea == ref else 0, False)
    rec_ref, alt, alt_copies = rec
    if ea == alt:
        return (alt_copies, True)
    if ea == rec_ref or ea == ref:
        # Effect allele is the reference allele; remaining copies carry it.
        return (2 - alt_copies, True)
    return (0, True)  # effect allele not present at this biallelic site


def _risk_band(percentile: float) -> str:
    if percentile >= 95:
        return "High"
    if percentile >= 80:
        return "Above average"
    if percentile >= 20:
        return "Average"
    return "Below average"


def _score_model(model: dict, index: PosIndex, rsid_index: dict[str, tuple[str, str, int]]) -> PrsTraitResult:
    raw = mu = var = 0.0
    observed = 0
    for v in model["variants"]:
        dose, was_observed = _dosage(v, index, rsid_index)
        w = v["weight"]
        p = v["sas_eaf"]
        raw += dose * w
        mu += 2 * p * w
        var += 2 * p * (1 - p) * w * w
        if was_observed:
            observed += 1

    sd = math.sqrt(var) if var > 0 else 0.0
    z = (raw - mu) / sd if sd > 0 else 0.0
    percentile = round(_phi(z) * 100, 1)

    return PrsTraitResult(
        trait=model["trait"],
        model_id=model["id"],
        ancestry=model["ancestry"],
        raw_score=round(raw, 4),
        reference_mean=round(mu, 4),
        reference_sd=round(sd, 4),
        z_score=round(z, 3),
        percentile=percentile,
        risk_band=_risk_band(percentile),
        variants_total=len(model["variants"]),
        variants_observed=observed,
    )


def run_prs(
    genotypes: dict[tuple[str, int, str, str], int],
    rsid_index: dict[str, tuple[str, str, int]] | None = None,
) -> PrsResponse:
    index = build_pos_index(genotypes)
    rsid_index = rsid_index or {}
    results = [_score_model(m, index, rsid_index) for m in MODELS]
    note = (
        "Illustrative polygenic scores for education, not clinical use. Percentiles are "
        "computed against a South-Asian reference distribution derived analytically from "
        "1000G SAS allele frequencies (Hardy-Weinberg + linkage-equilibrium approximation; "
        "LD is not modelled). Variant sites absent from the VCF are treated as homozygous "
        "reference — see variants_observed for how many were directly genotyped."
    )
    return PrsResponse(results=results, note=note)
