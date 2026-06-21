"""Pydantic request/response schemas for the annotation API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class VariantQuery(BaseModel):
    """A single variant to annotate, in normalized VCF coordinates (GRCh38)."""

    chrom: str = Field(..., description="Chromosome, e.g. '17' or 'chr17' or 'X'")
    pos: int = Field(..., ge=1, description="1-based position")
    ref: str = Field(..., description="Reference allele")
    alt: str = Field(..., description="Alternate allele")


class Annotation(BaseModel):
    """ClinVar annotation for one variant. Shape mirrors the project spec."""

    chrom: str
    pos: int
    ref: str
    alt: str
    gene: str | None = None
    variant: str | None = Field(default=None, description="dbSNP rsID, e.g. rs80357713")
    significance: str | None = Field(default=None, description="ClinVar CLNSIG")
    disease: str | None = Field(default=None, description="ClinVar CLNDN")
    clinvar_id: str | None = None
    matched: bool = Field(default=False, description="True if found in ClinVar")
    # gnomAD population allele frequencies (GRCh38). Differentiator: AF_sas.
    global_freq: float | None = Field(default=None, description="gnomAD overall allele frequency (AF)")
    south_asian_freq: float | None = Field(default=None, description="gnomAD South-Asian allele frequency (AF_sas)")


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
