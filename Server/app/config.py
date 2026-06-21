"""Application configuration.

Values are read from environment variables (or a local .env file). On the EC2
box, point CLINVAR_VCF at the tabix-indexed clinvar.vcf.gz pulled down from S3.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Genomic reference data ---------------------------------------------
    # Path to the bgzipped, tabix-indexed ClinVar VCF (clinvar.vcf.gz + .tbi).
    clinvar_vcf: Path = Path("data/clinvar.vcf.gz")

    # Optional dbSNP subset (e.g. chr22) for rsID lookups.
    dbsnp_vcf: Path | None = Path("data/dbsnp_chr22.vcf.gz")

    # Optional gnomAD subset (e.g. exomes chr22) for population allele frequencies.
    gnomad_vcf: Path | None = Path("data/gnomad_exomes_chr22.vcf.bgz")

    # --- AWS / S3 ------------------------------------------------------------
    s3_bucket: str = "indian-genomics-data"
    aws_region: str = "ap-south-1"

    # --- Results store -------------------------------------------------------
    # SQLite first; swap for a Postgres URL (postgresql+psycopg://...) later.
    database_url: str = "sqlite:///data/annotations.db"

    # --- Service -------------------------------------------------------------
    app_name: str = "GeneGenie Annotation Service"
    app_version: str = "0.1.0"


@lru_cache
def get_settings() -> Settings:
    return Settings()
