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
from .db import init_db, save_annotations
from .dbsnp import DbSnpLookup
from .gnomad import GnomadLookup
from .models import AnnotateResponse, Annotation, HealthResponse, VariantQuery
from .vcf_io import parse_vcf_text

settings = get_settings()
dbsnp = DbSnpLookup(settings.dbsnp_vcf)
gnomad = GnomadLookup(settings.gnomad_vcf)
annotator = ClinVarAnnotator(settings.clinvar_vcf, dbsnp=dbsnp, gnomad=gnomad)

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


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        version=settings.app_version,
        clinvar_loaded=annotator.available,
        dbsnp_loaded=dbsnp.available,
        gnomad_loaded=gnomad.available,
    )


@app.post("/annotate/variant", response_model=Annotation)
def annotate_variant(query: VariantQuery) -> Annotation:
    if not annotator.available:
        raise HTTPException(status_code=503, detail="ClinVar reference not loaded on server")
    return annotator.annotate(query)


@app.post("/annotate", response_model=AnnotateResponse)
async def annotate_vcf(file: UploadFile = File(...)) -> AnnotateResponse:
    if not annotator.available:
        raise HTTPException(status_code=503, detail="ClinVar reference not loaded on server")

    raw = await file.read()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Upload must be an uncompressed text VCF")

    variants = parse_vcf_text(text)
    if not variants:
        raise HTTPException(status_code=400, detail="No valid variant records found in VCF")

    annotations = annotator.annotate_many(variants)

    batch_id = uuid.uuid4().hex
    save_annotations(batch_id, annotations)

    return AnnotateResponse(count=len(annotations), annotations=annotations)
