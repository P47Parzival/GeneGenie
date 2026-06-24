#!/usr/bin/env bash
# Week 4 — build the gene knowledge-graph index from ClinVar + Reactome, push to S3.
set -euo pipefail

BUCKET="${S3_BUCKET:-indian-genomics-data}"
APP_DIR="${APP_DIR:-$HOME/genegenie}"
DATA="$HOME/data"
REACTOME_URL="https://reactome.org/download/current/NCBI2Reactome_All_Levels.txt"

mkdir -p "$DATA"
cd "$APP_DIR"

if [ ! -f "$DATA/clinvar.vcf.gz" ]; then
  echo "==> fetching ClinVar from S3 (needed to build the graph)"
  aws s3 cp "s3://$BUCKET/clinvar/clinvar.vcf.gz" "$DATA/clinvar.vcf.gz"
fi

echo "==> downloading Reactome NCBI2Reactome (CC-BY 4.0)"
wget -c -O "$DATA/NCBI2Reactome_All_Levels.txt" "$REACTOME_URL"

echo "==> building knowledge_graph.json"
.venv/bin/python -m app.build_kg \
  --clinvar "$DATA/clinvar.vcf.gz" \
  --reactome "$DATA/NCBI2Reactome_All_Levels.txt" \
  --out "$DATA/knowledge_graph.json"

echo "==> uploading to s3://$BUCKET/knowledge/"
aws s3 cp "$DATA/knowledge_graph.json" "s3://$BUCKET/knowledge/knowledge_graph.json"

echo "==> done. Restart the service to load KG_PATH."
