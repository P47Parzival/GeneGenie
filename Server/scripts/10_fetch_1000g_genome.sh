#!/usr/bin/env bash
# Genome-wide 1000 Genomes (GRCh38 phased) — sites-only (drop per-sample genotypes),
# keeping per-population AFs incl. SAS_AF. chr1-22 combined + tabix-indexed -> S3.
set -euo pipefail

BUCKET="${S3_BUCKET:-indian-genomics-data}"
BASE="http://ftp.1000genomes.ebi.ac.uk/vol1/ftp/data_collections/1000_genomes_project/release/20190312_biallelic_SNV_and_INDEL"
DATA="$HOME/data"; TMP="$DATA/onekg_tmp"

mkdir -p "$TMP"; cd "$TMP"
for c in $(seq 1 22); do
  f="ALL.chr${c}.shapeit2_integrated_snvindels_v2a_27022019.GRCh38.phased.vcf.gz"
  echo "==> chr${c}: download"
  wget -q -O "full_${c}.vcf.gz" "$BASE/$f"
  echo "==> chr${c}: sites-only"
  bcftools view -G -Oz -o "sites_${c}.vcf.gz" "full_${c}.vcf.gz"
  rm -f "full_${c}.vcf.gz"
done

echo "==> concat"
bcftools concat --threads 2 -Oz -o "$DATA/onekg_sas_genome.vcf.gz" \
  $(for c in $(seq 1 22); do echo "sites_${c}.vcf.gz"; done)
tabix -p vcf "$DATA/onekg_sas_genome.vcf.gz"

echo "==> upload to S3"
aws s3 cp "$DATA/onekg_sas_genome.vcf.gz"     "s3://$BUCKET/onekg/onekg_sas_genome.vcf.gz"
aws s3 cp "$DATA/onekg_sas_genome.vcf.gz.tbi" "s3://$BUCKET/onekg/onekg_sas_genome.vcf.gz.tbi"
rm -rf "$TMP"
echo "DONE 1000g genome-wide"
