"""Population context builder (Week 6 — the Indian population layer).

Combines South-Asian and global allele frequencies from multiple sources
(gnomAD AF_sas + 1000G SAS_AF) and produces the differentiating signal: whether
a variant is enriched or depleted in South Asians relative to the global
population. A variant that is rare globally but common in South Asians is a
classic interpretation trap — global-only tools may over-call it pathogenic,
when for an Indian patient it is likely benign.
"""

from __future__ import annotations

from .models import PopulationContext, PopulationFrequencies

# A variant is "enriched/depleted" when SAS and global differ by at least this
# fold-change, and the higher frequency is non-trivial (>= 1%).
FOLD_THRESHOLD = 3.0
MIN_MEANINGFUL_AF = 0.01


def _first_not_none(*values):
    for v in values:
        if v is not None:
            return v
    return None


def _pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    if value == 0:
        return "0%"
    if value < 0.0001:
        return f"{value:.1e}"
    return f"{value * 100:.3g}%"


def build_context(
    gnomad_global: float | None,
    gnomad_sas: float | None,
    onekg_global: float | None,
    onekg_sas: float | None,
) -> PopulationContext | None:
    sources: list[PopulationFrequencies] = []
    if gnomad_global is not None or gnomad_sas is not None:
        sources.append(PopulationFrequencies(source="gnomAD (exomes)", global_af=gnomad_global, south_asian_af=gnomad_sas))
    if onekg_global is not None or onekg_sas is not None:
        sources.append(PopulationFrequencies(source="1000G", global_af=onekg_global, south_asian_af=onekg_sas))

    if not sources:
        return None

    # Prefer gnomAD (larger cohort) for the headline numbers; fall back to 1000G.
    global_freq = _first_not_none(gnomad_global, onekg_global)
    south_asian_freq = _first_not_none(gnomad_sas, onekg_sas)

    comparison = "insufficient-data"
    note: str | None = None

    if global_freq is not None and south_asian_freq is not None:
        higher = max(global_freq, south_asian_freq)
        if higher < MIN_MEANINGFUL_AF:
            comparison = "concordant"
            note = "Rare in both South-Asian and global populations."
        else:
            # Guard divide-by-zero with a tiny epsilon.
            g = max(global_freq, 1e-9)
            s = max(south_asian_freq, 1e-9)
            if s / g >= FOLD_THRESHOLD and south_asian_freq >= MIN_MEANINGFUL_AF:
                comparison = "population-enriched"
                note = (
                    f"Common in South Asians ({_pct(south_asian_freq)}) but rarer globally "
                    f"({_pct(global_freq)}). Global-only rarity filters may over-flag this variant; "
                    f"for a South-Asian patient it is more likely benign."
                )
            elif g / s >= FOLD_THRESHOLD and global_freq >= MIN_MEANINGFUL_AF:
                comparison = "population-depleted"
                note = (
                    f"Less common in South Asians ({_pct(south_asian_freq)}) than globally "
                    f"({_pct(global_freq)})."
                )
            else:
                comparison = "concordant"
                note = f"Similar frequency in South Asians ({_pct(south_asian_freq)}) and globally ({_pct(global_freq)})."

    return PopulationContext(
        global_freq=global_freq,
        south_asian_freq=south_asian_freq,
        sources=sources,
        comparison=comparison,
        note=note,
    )
