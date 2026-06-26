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


def _pick(genome_path: Path | None, chr22_path: Path | None) -> tuple[Path | None, frozenset[str] | None, str]:
    """Prefer a genome-wide file if it exists, else the chr22 subset.
    Returns (path, contigs, scope-label). contigs=None means genome-wide."""
    if genome_path and genome_path.exists():
        return genome_path, None, "genome-wide"
    return chr22_path, frozenset({"22"}), "chr22"


def build_registry(settings: Settings | None = None) -> dict[str, ReferenceDataset]:
    s = settings or get_settings()
    bucket = f"s3://{s.s3_bucket}"

    gnomad_path, gnomad_contigs, gnomad_scope = _pick(s.gnomad_vcf_genome, s.gnomad_vcf)
    onekg_path, onekg_contigs, onekg_scope = _pick(s.onekg_vcf_genome, s.onekg_vcf)
    revel_path, revel_contigs, revel_scope = _pick(s.revel_path_genome, s.revel_path)

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
            key="gnomad", label="gnomAD", detail=f"exomes {gnomad_scope} · AF_sas",
            category="population", source="gnomAD v4.1 exomes",
            local_path=gnomad_path, s3_uri=f"{bucket}/gnomad/",
            contigs=gnomad_contigs,
        ),
        ReferenceDataset(
            key="onekg", label="1000G", detail=f"SAS {onekg_scope} · SAS_AF",
            category="population", source="1000 Genomes (GRCh38)",
            local_path=onekg_path, s3_uri=f"{bucket}/onekg/",
            contigs=onekg_contigs,
        ),
        ReferenceDataset(
            key="knowledge", label="Knowledge Graph", detail="gene → disease/drug/pathway",
            category="knowledge", source="ClinVar + Reactome + CPIC/PharmGKB",
            local_path=s.kg_path, s3_uri=f"{bucket}/knowledge/knowledge_graph.json",
            requires_index=False, contigs=None,
        ),
        ReferenceDataset(
            key="revel", label="REVEL", detail=f"missense {revel_scope} · PP3/BP4",
            category="predictor", source="REVEL v1.3 (Zenodo 7072866)",
            local_path=revel_path, s3_uri=f"{bucket}/revel/",
            contigs=revel_contigs,
        ),
    ]
    return {d.key: d for d in datasets}
