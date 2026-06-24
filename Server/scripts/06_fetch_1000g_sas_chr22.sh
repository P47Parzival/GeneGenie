#!/usr/bin/env bash
# Week 6 — 1000 Genomes SAS (South Asian) allele frequencies, chr22 subset.
# The GRCh38 phased release carries per-superpopulation AFs in INFO (incl. SAS_AF),
# so we just download chr22, drop genotypes (sites-only), and index.
set -euo pipefail

BUCKET="${S3_BUCKET:-indian-genomics-data}"
URL="http://ftp.1000genomes.ebi.ac.uk/vol1/ftp/data_collections/1000_genomes_project/release/20190312_biallelic_SNV_and_INDEL/ALL.chr22.shapeit2_integrated_snvindels_v2a_27022019.GRCh38.phased.vcf.gz"
RAW="$HOME/data/onekg_chr22.full.vcf.gz"
SITES="$HOME/data/onekg_sas_chr22.vcf.gz"

mkdir -p "$HOME/data"
cd "$HOME/data"

echo "==> downloading 1000G chr22 GRCh38 (phased, ~185 MB)"
wget -c -O "$RAW" "$URL"

echo "==> stripping to sites-only (keep INFO/AF fields, drop 2548 genotypes)"
bcftools view -G -Oz -o "$SITES" "$RAW"
tabix -p vcf "$SITES"

echo "==> sanity: SAS_AF present?"
tabix "$SITES" 22:16050000-16060000 | head -1 | tr ';' '\n' | grep -E '^(AF|SAS_AF)=' || true

echo "==> uploading sites-only to s3://$BUCKET/onekg/"
aws s3 cp "$SITES"      "s3://$BUCKET/onekg/onekg_sas_chr22.vcf.gz"
aws s3 cp "$SITES.tbi"  "s3://$BUCKET/onekg/onekg_sas_chr22.vcf.gz.tbi"

echo "==> cleaning up full genotype file to save EBS"
rm -f "$RAW"
echo "==> done. Restart the service to pick up ONEKG_VCF."
