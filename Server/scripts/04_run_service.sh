#!/usr/bin/env bash
# Pull ClinVar onto the EBS "workbench" (if not already there), then run the API.
set -euo pipefail

BUCKET="${S3_BUCKET:-indian-genomics-data}"
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_DIR="${DATA_DIR:-$HOME/data}"
cd "$APP_DIR"

mkdir -p "$DATA_DIR"
if [ ! -f "$DATA_DIR/clinvar.vcf.gz" ]; then
  echo "==> fetching ClinVar from s3://$BUCKET/clinvar/ to $DATA_DIR (EBS workbench)"
  aws s3 cp "s3://$BUCKET/clinvar/clinvar.vcf.gz"     "$DATA_DIR/clinvar.vcf.gz"
  aws s3 cp "s3://$BUCKET/clinvar/clinvar.vcf.gz.tbi" "$DATA_DIR/clinvar.vcf.gz.tbi"
else
  echo "==> ClinVar already present at $DATA_DIR (skipping S3 download)"
fi

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

export CLINVAR_VCF="$DATA_DIR/clinvar.vcf.gz"
export DATABASE_URL="${DATABASE_URL:-sqlite:///$DATA_DIR/annotations.db}"

echo "==> starting service on 0.0.0.0:8000 (CLINVAR_VCF=$CLINVAR_VCF)"
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
