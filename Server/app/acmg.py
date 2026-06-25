"""ACMG/AMP variant classification engine (Week 3).

HONEST SCOPE: this implements only the criteria we can actually evidence today
from the data we have loaded (gnomAD allele frequencies + ClinVar assertions):

  - PM2_Supporting : rare/absent in gnomAD            (ClinGen SVI downgraded PM2 to Supporting)
  - BS1            : AF >= 1%  (too common for most Mendelian disease)
  - BA1            : AF >= 5%  (stand-alone benign)
  - PP5 / BP6      : ClinVar asserts pathogenic/benign (strength scaled by review stars)
  - PP3 / BP4      : in-silico predictor (REVEL), ClinGen-calibrated strengths

NOT yet implemented (need data we haven't added):
  - PVS1 (LoF + gene mechanism), PS1/PM5 (protein-level), PS3/BS3 (functional), PM1, etc.

Criteria are combined with the ACMG 2015 (Richards et al.) rules. Because our
criteria set is small, most novel variants resolve to Uncertain Significance —
that is the correct, honest outcome, not a bug. For variants ClinVar has already
reviewed (>=1 star, non-conflicting), we surface ClinVar's call as the headline
and record how it was derived in `basis`.
"""

from __future__ import annotations

from .models import EvidenceItem

# Strengths
STAND_ALONE = "stand_alone"
VERY_STRONG = "very_strong"
STRONG = "strong"
MODERATE = "moderate"
SUPPORTING = "supporting"

# 5-tier classifications
PATHOGENIC = "Pathogenic"
LIKELY_PATHOGENIC = "Likely Pathogenic"
VUS = "Uncertain Significance"
LIKELY_BENIGN = "Likely Benign"
BENIGN = "Benign"

# Population-frequency thresholds (allele frequency).
BA1_AF = 0.05
BS1_AF = 0.01
PM2_AF = 0.0001

# REVEL thresholds — ClinGen SVI calibrated (Pejaver et al. 2022).
REVEL_PP3_STRONG = 0.932
REVEL_PP3_MODERATE = 0.773
REVEL_PP3_SUPPORTING = 0.644
REVEL_BP4_STRONG = 0.016
REVEL_BP4_SUPPORTING = 0.290


def _predictor_evidence(revel: float | None) -> list[EvidenceItem]:
    if revel is None:
        return []
    if revel >= REVEL_PP3_STRONG:
        return [EvidenceItem(code="PP3_Strong", category="pathogenic", strength=STRONG,
                             description=f"REVEL {revel:.3f} — strong in-silico support for damage", source="REVEL")]
    if revel >= REVEL_PP3_MODERATE:
        return [EvidenceItem(code="PP3_Moderate", category="pathogenic", strength=MODERATE,
                             description=f"REVEL {revel:.3f} — moderate in-silico support for damage", source="REVEL")]
    if revel >= REVEL_PP3_SUPPORTING:
        return [EvidenceItem(code="PP3", category="pathogenic", strength=SUPPORTING,
                             description=f"REVEL {revel:.3f} — supporting in-silico evidence for damage", source="REVEL")]
    if revel <= REVEL_BP4_STRONG:
        return [EvidenceItem(code="BP4_Strong", category="benign", strength=STRONG,
                             description=f"REVEL {revel:.3f} — strong in-silico support for tolerance", source="REVEL")]
    if revel <= REVEL_BP4_SUPPORTING:
        return [EvidenceItem(code="BP4", category="benign", strength=SUPPORTING,
                             description=f"REVEL {revel:.3f} — supporting in-silico evidence for tolerance", source="REVEL")]
    return []  # 0.290–0.644: indeterminate, no criterion


def review_to_stars(review_status: str | None) -> int:
    """Map ClinVar CLNREVSTAT to a 0-4 star confidence level."""
    if not review_status:
        return 0
    s = review_status.lower()
    if "practice_guideline" in s:
        return 4
    if "reviewed_by_expert_panel" in s:
        return 3
    if "multiple_submitters" in s and "no_conflict" in s:
        return 2
    if "conflicting" in s:
        return 1
    if "single_submitter" in s and "criteria_provided" in s:
        return 1
    return 0


def _population_evidence(global_freq, sas_freq, covered: bool) -> list[EvidenceItem]:
    if not covered:
        return []  # we cannot speak to frequency outside the loaded subsets
    # Common in ANY queried population leans benign; track which population drives it.
    candidates = [(f, lbl) for f, lbl in ((global_freq, "global"), (sas_freq, "South Asian")) if f is not None]
    if not candidates:
        return [
            EvidenceItem(
                code="PM2_Supporting",
                category="pathogenic",
                strength=SUPPORTING,
                description="Absent from population references (loaded subset)",
                source="population",
            )
        ]
    af, which = max(candidates, key=lambda x: x[0])
    pop = f" ({which})" if which == "South Asian" else ""
    if af >= BA1_AF:
        return [EvidenceItem(code="BA1", category="benign", strength=STAND_ALONE,
                             description=f"Allele frequency {af:.3%}{pop} ≥ 5%", source="population")]
    if af >= BS1_AF:
        return [EvidenceItem(code="BS1", category="benign", strength=STRONG,
                             description=f"Allele frequency {af:.3%}{pop} ≥ 1%", source="population")]
    if af < PM2_AF:
        return [EvidenceItem(code="PM2_Supporting", category="pathogenic", strength=SUPPORTING,
                             description=f"Allele frequency {af:.4%} < 0.01% in population references", source="population")]
    return []  # 0.01%–1%: no population criterion applies


def _clinvar_evidence(significance: str | None, stars: int) -> list[EvidenceItem]:
    if not significance:
        return []
    s = significance.lower()
    if "conflicting" in s or "uncertain" in s:
        return []
    strength = STRONG if stars >= 2 else SUPPORTING
    label = significance.replace("_", " ")
    if "pathogenic" in s and "benign" not in s:
        return [EvidenceItem(code="PP5", category="pathogenic", strength=strength,
                             description=f"ClinVar: {label} ({stars}★)", source="ClinVar")]
    if "benign" in s:
        return [EvidenceItem(code="BP6", category="benign", strength=strength,
                             description=f"ClinVar: {label} ({stars}★)", source="ClinVar")]
    return []


def _combine(evidence: list[EvidenceItem]) -> str:
    """Apply ACMG 2015 combining rules to the applied criteria."""
    pvs = sum(1 for e in evidence if e.category == "pathogenic" and e.strength == VERY_STRONG)
    ps = sum(1 for e in evidence if e.category == "pathogenic" and e.strength == STRONG)
    pm = sum(1 for e in evidence if e.category == "pathogenic" and e.strength == MODERATE)
    pp = sum(1 for e in evidence if e.category == "pathogenic" and e.strength == SUPPORTING)
    ba = sum(1 for e in evidence if e.category == "benign" and e.strength == STAND_ALONE)
    bs = sum(1 for e in evidence if e.category == "benign" and e.strength == STRONG)
    bp = sum(1 for e in evidence if e.category == "benign" and e.strength == SUPPORTING)

    pathogenic = (
        (pvs >= 1 and (ps >= 1 or pm >= 2 or (pm >= 1 and pp >= 1) or pp >= 2))
        or ps >= 2
        or (ps == 1 and (pm >= 3 or (pm >= 2 and pp >= 2) or (pm >= 1 and pp >= 4)))
    )
    likely_pathogenic = (
        (pvs >= 1 and pm >= 1)
        or (ps == 1 and 1 <= pm <= 2)
        or (ps == 1 and pp >= 2)
        or pm >= 3
        or (pm >= 2 and pp >= 2)
        or (pm >= 1 and pp >= 4)
    )
    benign = ba >= 1 or bs >= 2
    likely_benign = (bs >= 1 and bp >= 1) or bp >= 2

    path_side = pathogenic or likely_pathogenic
    benign_side = benign or likely_benign

    # Contradictory evidence -> Uncertain (per ACMG, conflicting criteria = VUS).
    if path_side and benign_side:
        return VUS
    if pathogenic:
        return PATHOGENIC
    if likely_pathogenic:
        return LIKELY_PATHOGENIC
    if benign:
        return BENIGN
    if likely_benign:
        return LIKELY_BENIGN
    return VUS


def _clinvar_to_tier(significance: str | None) -> str | None:
    if not significance:
        return None
    s = significance.lower()
    if "conflicting" in s or "uncertain" in s:
        return VUS
    if "pathogenic" in s and "benign" not in s:
        return LIKELY_PATHOGENIC if s.startswith("likely") else PATHOGENIC
    if "benign" in s:
        return LIKELY_BENIGN if s.startswith("likely") else BENIGN
    return None


def classify(
    global_freq,
    sas_freq,
    covered: bool,
    significance: str | None,
    review_status: str | None,
    revel_score: float | None = None,
) -> tuple[str, str, list[EvidenceItem]]:
    """Return (classification, basis, evidence)."""
    stars = review_to_stars(review_status)
    evidence = _population_evidence(global_freq, sas_freq, covered)
    evidence += _clinvar_evidence(significance, stars)
    evidence += _predictor_evidence(revel_score)

    computed = _combine(evidence)

    # Reconcile: a reviewed ClinVar assertion (>=1 star, non-conflicting) is the
    # clinical headline; our computed call provides independent support/contrast.
    clinvar_tier = _clinvar_to_tier(significance)
    if clinvar_tier and clinvar_tier != VUS and stars >= 1:
        return clinvar_tier, f"ClinVar assertion ({stars}★)", evidence

    return computed, "ACMG criteria (computed)", evidence
