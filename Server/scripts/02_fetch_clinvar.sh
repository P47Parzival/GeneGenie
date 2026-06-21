#!/usr/bin/env bash
# Step 4 — download ClinVar (GRCh38) and push to S3.
set -euo pipefail

BUCKET="${S3_BUCKET:-indian-genomics-data}"
BASE="https://ftp.ncbi.nlm.nih.gov/pub/clinvar/vcf_GRCh38"

mkdir -p ~/data
cd ~/data

echo "==> downloading ClinVar VCF + index"
wget -c "$BASE/clinvar.vcf.gz"
wget -c "$BASE/clinvar.vcf.gz.tbi"

echo "==> sanity check (record count via tabix)"
tabix -l clinvar.vcf.gz | head

echo "==> uploading to s3://$BUCKET/clinvar/"
aws s3 cp clinvar.vcf.gz     "s3://$BUCKET/clinvar/clinvar.vcf.gz"
aws s3 cp clinvar.vcf.gz.tbi "s3://$BUCKET/clinvar/clinvar.vcf.gz.tbi"

echo "==> ClinVar now in S3. Files also kept locally at ~/data for the service."
