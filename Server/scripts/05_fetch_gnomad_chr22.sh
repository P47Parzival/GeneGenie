#!/usr/bin/env bash
# Step 8 — gnomAD v4.1 EXOMES chr22 (largest South-Asian cohort -> AF_sas).
# Source: AWS Open Data (no credentials needed via --no-sign-request, us-east-1).
set -euo pipefail

BUCKET="${S3_BUCKET:-indian-genomics-data}"
SRC_BUCKET="s3://gnomad-public-us-east-1/release/4.1/vcf/exomes"
SRC_FILE="gnomad.exomes.v4.1.sites.chr22.vcf.bgz"
DEST="$HOME/data/gnomad_exomes_chr22.vcf.bgz"

mkdir -p "$HOME/data"
cd "$HOME/data"

echo "==> source size:"
aws s3 ls --no-sign-request --region us-east-1 "$SRC_BUCKET/$SRC_FILE"

echo "==> downloading gnomAD exomes chr22 (+ .tbi) from AWS Open Data"
aws s3 cp --no-sign-request --region us-east-1 "$SRC_BUCKET/$SRC_FILE"      "$DEST"
aws s3 cp --no-sign-request --region us-east-1 "$SRC_BUCKET/$SRC_FILE.tbi"  "$DEST.tbi"

echo "==> sanity: confirm AF_sas present in a record"
tabix "$DEST" chr22:10000000-11000000 | head -1 | tr ';' '\n' | grep -E '^AF(_sas)?=' | head -5 || true

echo "==> uploading to s3://$BUCKET/gnomad/"
aws s3 cp "$DEST"     "s3://$BUCKET/gnomad/gnomad_exomes_chr22.vcf.bgz"
aws s3 cp "$DEST.tbi" "s3://$BUCKET/gnomad/gnomad_exomes_chr22.vcf.bgz.tbi"

echo "==> done. Restart the service so it picks up GNOMAD_VCF."
