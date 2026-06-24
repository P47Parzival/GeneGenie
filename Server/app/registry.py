"""Reference-data registry — single source of truth for loaded datasets.

Every reference dataset (ClinVar, dbSNP, gnomAD, 1000G, and future predictors /
knowledge-graph sources) is declared once here with its metadata, local path,
S3 location, and chromosome coverage. Lookup classes and the API derive
availability and `covers()` from these entries instead of hardcoding paths and
contig sets in multiple files. Adding a dataset = one entry below.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from .config import Settings, get_settings


@dataclass(frozen=True)
class ReferenceDataset:
    key: str
    label: str
    detail: str
    category: str           # clinical | annotation | population | pharmacogenomics | knowledge
    source: str
    local_path: Path | None
    s3_uri: str | None = None
    requires_index: bool = True
    index_suffix: str = ".tbi"
    contigs: frozenset[str] | None = None  # None => genome-wide

    def available(self) -> bool:
        if not self.local_path or not self.local_path.exists():
            return False
        if self.requires_index:
            index = self.local_path.with_suffix(self.local_path.suffix + self.index_suffix)
            if not index.exists() or shutil.which("tabix") is None:
                return False
        return True

    def covers(self, chrom: str) -> bool:
        if self.contigs is None:
            return True
        return chrom.replace("chr", "") in self.contigs

    @property
    def genome_wide(self) -> bool:
        return self.contigs is None


def build_registry(settings: Settings | None = None) -> dict[str, ReferenceDataset]:
    s = settings or get_settings()
    bucket = f"s3://{s.s3_bucket}"
    datasets = [
        ReferenceDataset(
            key="clinvar", label="ClinVar", detail="GRCh38 · full",
            category="clinical", source="NCBI ClinVar (GRCh38)",
            local_path=s.clinvar_vcf, s3_uri=f"{bucket}/clinvar/clinvar.vcf.gz",
            contigs=None,
        ),
        ReferenceDataset(
            key="dbsnp", label="dbSNP", detail="chr22 subset",
            category="annotation", source="NCBI dbSNP",
            local_path=s.dbsnp_vcf, s3_uri=f"{bucket}/dbsnp/dbsnp_chr22.vcf.gz",
            contigs=frozenset({"22"}),
        ),
        ReferenceDataset(
            key="gnomad", label="gnomAD", detail="exomes chr22 · AF_sas",
            category="population", source="gnomAD v4.1 exomes",
            local_path=s.gnomad_vcf, s3_uri=f"{bucket}/gnomad/gnomad_exomes_chr22.vcf.bgz",
            contigs=frozenset({"22"}),
        ),
        ReferenceDataset(
            key="onekg", label="1000G", detail="SAS chr22 · SAS_AF",
            category="population", source="1000 Genomes (GRCh38)",
            local_path=s.onekg_vcf, s3_uri=f"{bucket}/onekg/onekg_sas_chr22.vcf.gz",
            contigs=frozenset({"22"}),
        ),
        ReferenceDataset(
            key="knowledge", label="Knowledge Graph", detail="gene → disease/drug/pathway",
            category="knowledge", source="ClinVar + Reactome + CPIC/PharmGKB",
            local_path=s.kg_path, s3_uri=f"{bucket}/knowledge/knowledge_graph.json",
            requires_index=False, contigs=None,
        ),
    ]
    return {d.key: d for d in datasets}
