"""Pydantic request/response schemas for the annotation API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class VariantQuery(BaseModel):
    """A single variant to annotate, in normalized VCF coordinates (GRCh38)."""

    chrom: str = Field(..., description="Chromosome, e.g. '17' or 'chr17' or 'X'")
    pos: int = Field(..., ge=1, description="1-based position")
    ref: str = Field(..., description="Reference allele")
    alt: str = Field(..., description="Alternate allele")


class PopulationFrequencies(BaseModel):
    """Allele frequencies from one population reference."""

    source: str = Field(..., description="e.g. gnomAD (exomes), 1000G")
    global_af: float | None = None
    south_asian_af: float | None = None


class PopulationContext(BaseModel):
    """Combined South-Asian vs global frequency view across sources (Week 6)."""

    global_freq: float | None = Field(default=None, description="Best available global AF")
    south_asian_freq: float | None = Field(default=None, description="Best available South-Asian AF")
    sources: list[PopulationFrequencies] = Field(default_factory=list)
    comparison: str = Field(
        default="insufficient-data",
        description="population-enriched | population-depleted | concordant | insufficient-data",
    )
    note: str | None = Field(default=None, description="Plain-language interpretation of the SAS-vs-global signal")


class EvidenceItem(BaseModel):
    """One applied ACMG/AMP criterion (or population/source-derived evidence)."""

    code: str = Field(..., description="ACMG criterion code, e.g. PM2_Supporting, BA1, BS1, PP5")
    category: str = Field(..., description="'pathogenic' or 'benign'")
    strength: str = Field(..., description="stand_alone | very_strong | strong | moderate | supporting")
    description: str = Field(..., description="Human-readable basis for the criterion")
    source: str = Field(..., description="Evidence source, e.g. gnomAD, ClinVar")


class Annotation(BaseModel):
    """ClinVar annotation for one variant, enriched with frequencies + ACMG call."""

    chrom: str
    pos: int
    ref: str
    alt: str
    gene: str | None = None
    variant: str | None = Field(default=None, description="dbSNP rsID, e.g. rs80357713")
    significance: str | None = Field(default=None, description="ClinVar CLNSIG")
    review_status: str | None = Field(default=None, description="ClinVar CLNREVSTAT")
    disease: str | None = Field(default=None, description="ClinVar CLNDN")
    clinvar_id: str | None = None
    matched: bool = Field(default=False, description="True if found in ClinVar")
    # gnomAD population allele frequencies (GRCh38). Differentiator: AF_sas.
    global_freq: float | None = Field(default=None, description="gnomAD overall allele frequency (AF)")
    south_asian_freq: float | None = Field(default=None, description="gnomAD South-Asian allele frequency (AF_sas)")
    # Indian population layer (Week 6): SAS-vs-global context across sources.
    population: PopulationContext | None = None
    # ACMG classification (Week 3 engine).
    acmg_classification: str | None = Field(
        default=None, description="Pathogenic | Likely Pathogenic | Uncertain Significance | Likely Benign | Benign"
    )
    acmg_basis: str | None = Field(default=None, description="How the headline classification was derived")
    acmg_evidence: list[EvidenceItem] = Field(default_factory=list)


class AnnotateResponse(BaseModel):
    count: int
    annotations: list[Annotation]


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str
    clinvar_loaded: bool
    dbsnp_loaded: bool
    gnomad_loaded: bool
    onekg_loaded: bool


# --- Portal dashboard stats -------------------------------------------------

class ReferenceDatasetInfo(BaseModel):
    key: str
    label: str
    detail: str
    category: str
    source: str
    genome_wide: bool
    loaded: bool


class ReferencesResponse(BaseModel):
    datasets: list[ReferenceDatasetInfo]


class StatsMetrics(BaseModel):
    total_annotations: int
    total_batches: int
    matched_count: int
    pathogenic_count: int
    match_rate: float  # 0..1, matched / total


class SignificanceBucket(BaseModel):
    label: str
    count: int


class RecentVariant(BaseModel):
    chrom: str
    pos: int
    ref: str
    alt: str
    gene: str | None = None
    variant: str | None = None
    significance: str | None = None
    matched: bool = False
    created_at: str


class StatsResponse(BaseModel):
    metrics: StatsMetrics
    significance: list[SignificanceBucket]
    recent: list[RecentVariant]


# --- Pharmacogenomics (Week 8) ----------------------------------------------

class PgxDrugGuidance(BaseModel):
    drug: str
    recommendation: str
    source: str = "CPIC"


class PgxGeneResult(BaseModel):
    gene: str
    diplotype: str = Field(..., description="e.g. *1/*2")
    phenotype: str = Field(..., description="e.g. Intermediate Metabolizer")
    detected: list[str] = Field(default_factory=list, description="Detected non-reference alleles/variants")
    drugs: list[PgxDrugGuidance] = Field(default_factory=list)


class PgxReport(BaseModel):
    genes_tested: list[str]
    results: list[PgxGeneResult]
    note: str


# --- Gene knowledge graph (Week 4) ------------------------------------------

class DiseaseAssociation(BaseModel):
    name: str
    count: int = Field(..., description="Number of pathogenic ClinVar variants linking gene to disease")


class DrugAssociation(BaseModel):
    drug: str
    effect: str


class GeneVariantStats(BaseModel):
    pathogenic: int = 0
    benign: int = 0
    uncertain: int = 0
    conflicting: int = 0
    total: int = 0


class GeneNode(BaseModel):
    symbol: str
    ncbi_id: str | None = None
    diseases: list[DiseaseAssociation] = Field(default_factory=list)
    drugs: list[DrugAssociation] = Field(default_factory=list)
    pathways: list[str] = Field(default_factory=list)
    variant_stats: GeneVariantStats = Field(default_factory=GeneVariantStats)
