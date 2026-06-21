#!/usr/bin/env bash
# Step 5 — grab ONLY a dbSNP subset (chr22) instead of the full multi-hundred-GB file.
# dbSNP GCF_000001405.40 uses RefSeq accessions; chromosome 22 (GRCh38) = NC_000022.11.
set -euo pipefail

BUCKET="${S3_BUCKET:-indian-genomics-data}"
BASE="https://ftp.ncbi.nlm.nih.gov/snp/latest_release/VCF"
CHR22_ACCESSION="NC_000022.11"

mkdir -p ~/data
cd ~/data

echo "==> downloading dbSNP index (small) to enable a ranged slice"
wget -c "$BASE/GCF_000001405.40.gz.tbi"

# Stream only chr22 out of the remote file using tabix over HTTP, then re-block-gzip.
echo "==> slicing chr22 ($CHR22_ACCESSION) directly from the remote dbSNP VCF"
tabix -h "$BASE/GCF_000001405.40.gz" "$CHR22_ACCESSION" \
  | bgzip > dbsnp_chr22.vcf.gz
tabix -p vcf dbsnp_chr22.vcf.gz

echo "==> uploading chr22 subset to S3"
aws s3 cp dbsnp_chr22.vcf.gz     "s3://$BUCKET/dbsnp/dbsnp_chr22.vcf.gz"
aws s3 cp dbsnp_chr22.vcf.gz.tbi "s3://$BUCKET/dbsnp/dbsnp_chr22.vcf.gz.tbi"

echo "==> done. Full dbSNP indexes can come later."
