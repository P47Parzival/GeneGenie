#!/usr/bin/env bash
# Genome-wide gnomAD exomes — slimmed to just AF + AF_sas (the only fields we use),
# which shrinks each chromosome ~130x (e.g. chr21 2.1 GB -> 16 MB). One combined,
# tabix-indexed sites file across chr1-22 + X -> S3.
set -euo pipefail

BUCKET="${S3_BUCKET:-indian-genomics-data}"
SRC="s3://gnomad-public-us-east-1/release/4.1/vcf/exomes"
DATA="$HOME/data"; TMP="$DATA/gnomad_tmp"
CHROMS="1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 X"

mkdir -p "$TMP"; cd "$TMP"
for c in $CHROMS; do
  f="gnomad.exomes.v4.1.sites.chr${c}.vcf.bgz"
  echo "==> chr${c}: download"
  aws s3 cp --no-sign-request --region us-east-1 "$SRC/$f" "$f"
  echo "==> chr${c}: slim to AF,AF_sas"
  bcftools annotate -x "^INFO/AF,INFO/AF_sas" --threads 2 -Oz -o "slim_${c}.vcf.gz" "$f"
  rm -f "$f"
done

echo "==> concat all chromosomes"
bcftools concat --threads 2 -Oz -o "$DATA/gnomad_exomes_genome.vcf.bgz" \
  $(for c in $CHROMS; do echo "slim_${c}.vcf.gz"; done)
tabix -p vcf "$DATA/gnomad_exomes_genome.vcf.bgz"

echo "==> upload to S3"
aws s3 cp "$DATA/gnomad_exomes_genome.vcf.bgz"     "s3://$BUCKET/gnomad/gnomad_exomes_genome.vcf.bgz"
aws s3 cp "$DATA/gnomad_exomes_genome.vcf.bgz.tbi" "s3://$BUCKET/gnomad/gnomad_exomes_genome.vcf.bgz.tbi"
rm -rf "$TMP"
echo "DONE gnomad genome-wide"
