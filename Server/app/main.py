"""GeneGenie annotation service.

Pipeline (Step 7 of the build plan):
    user.vcf  ->  parse variants  ->  ClinVar lookup  ->  JSON (+ persisted)
"""

from __future__ import annotations

import uuid

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .clinvar import ClinVarAnnotator
from .config import get_settings
from .db import get_stats, init_db, save_annotations
from .dbsnp import DbSnpLookup
from .gnomad import GnomadLookup
from .knowledge import KnowledgeGraph
from .onekg import OneKGenomesSAS
from .models import (
    AnnotateResponse,
    Annotation,
    HealthResponse,
    GeneNode,
    PgxReport,
    PrsResponse,
    ReferenceDatasetInfo,
    ReferencesResponse,
    StatsResponse,
    VariantQuery,
)
from .pgx import defining_positions, defining_rsids, run_pgx
from .prs import model_positions, model_rsids, run_prs
from .registry import build_registry
from .vcf_io import parse_vcf_genotypes_stream, parse_vcf_text_stream
from fastapi.concurrency import run_in_threadpool

settings = get_settings()
registry = build_registry(settings)
dbsnp = DbSnpLookup(registry["dbsnp"])
gnomad = GnomadLookup(registry["gnomad"])
onekg = OneKGenomesSAS(registry["onekg"])
annotator = ClinVarAnnotator(registry["clinvar"], dbsnp=dbsnp, gnomad=gnomad, onekg=onekg)
knowledge = KnowledgeGraph(settings.kg_path)

app = FastAPI(title=settings.app_name, version=settings.app_version)

# Allow the Next.js frontend (dev + deployed) to call the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    init_db()
    knowledge.load()


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        version=settings.app_version,
        clinvar_loaded=annotator.available,
        dbsnp_loaded=dbsnp.available,
        gnomad_loaded=gnomad.available,
        onekg_loaded=onekg.available,
    )


@app.get("/gene/{symbol}", response_model=GeneNode)
def gene(symbol: str) -> GeneNode:
    if not knowledge.available:
        raise HTTPException(status_code=503, detail="Knowledge graph not loaded on server")
    node = knowledge.get_gene(symbol)
    if node is None:
        raise HTTPException(status_code=404, detail=f"Gene '{symbol}' not found in knowledge graph")
    return GeneNode(**node)


@app.get("/references", response_model=ReferencesResponse)
def references() -> ReferencesResponse:
    return ReferencesResponse(
        datasets=[
            ReferenceDatasetInfo(
                key=d.key,
                label=d.label,
                detail=d.detail,
                category=d.category,
                source=d.source,
                genome_wide=d.genome_wide,
                loaded=d.available(),
            )
            for d in registry.values()
        ]
    )


@app.post("/pgx", response_model=PgxReport)
async def pharmacogenomics(file: UploadFile = File(...)) -> PgxReport:
    # Stream off the event loop; retain PGx-defining positions and rsIDs.
    genotypes, rsid_index, had_gt = await run_in_threadpool(
        parse_vcf_genotypes_stream, file.file, defining_positions(), defining_rsids()
    )
    return run_pgx(genotypes, rsid_index, had_gt)


@app.post("/prs", response_model=PrsResponse)
async def polygenic_risk(file: UploadFile = File(...)) -> PrsResponse:
    # Stream off the event loop; retain PRS model positions and rsIDs.
    genotypes, rsid_index, _had_gt = await run_in_threadpool(
        parse_vcf_genotypes_stream, file.file, model_positions(), model_rsids()
    )
    return run_prs(genotypes, rsid_index)


@app.get("/stats", response_model=StatsResponse)
def stats() -> StatsResponse:
    metrics, significance, recent = get_stats()
    return StatsResponse(metrics=metrics, significance=significance, recent=recent)


@app.post("/annotate/variant", response_model=Annotation)
def annotate_variant(query: VariantQuery) -> Annotation:
    if not annotator.available:
        raise HTTPException(status_code=503, detail="ClinVar reference not loaded on server")
    return annotator.annotate(query)


@app.post("/annotate", response_model=AnnotateResponse)
async def annotate_vcf(file: UploadFile = File(...)) -> AnnotateResponse:
    if not annotator.available:
        raise HTTPException(status_code=503, detail="ClinVar reference not loaded on server")

    # Stream off the event loop; cap at max_variants (annotating a whole WGS VCF
    # one ClinVar lookup at a time is not the intended use — see README).
    variants, truncated = await run_in_threadpool(parse_vcf_text_stream, file.file)
    if not variants:
        raise HTTPException(status_code=400, detail="No valid variant records found in VCF")

    annotations = await run_in_threadpool(annotator.annotate_many, variants)

    batch_id = uuid.uuid4().hex
    save_annotations(batch_id, annotations)

    return AnnotateResponse(count=len(annotations), annotations=annotations, truncated=truncated)
