#!/usr/bin/env bash
# Predictor layer — REVEL chr22 missense scores (GRCh38), tabix-indexed -> S3.
# REVEL is a missense pathogenicity predictor (0-1); we use the ClinGen-calibrated
# thresholds for ACMG PP3/BP4. Source: Zenodo 7072866 (revel-v1.3).
set -euo pipefail

BUCKET="${S3_BUCKET:-indian-genomics-data}"
DATA="$HOME/data"
URL="https://zenodo.org/record/7072866/files/revel-v1.3_all_chromosomes.zip"

mkdir -p "$DATA"
cd "$DATA"

if [ ! -f revel_with_transcript_ids ]; then
  echo "==> downloading REVEL (~526 MB) + unzip (~6 GB)"
  wget -q -O revel.zip "$URL"
  unzip -o revel.zip
fi

echo "==> extracting chr22 GRCh38 rows (dedup across transcripts)"
# CSV: chr,hg19_pos,grch38_pos,ref,alt,aaref,aaalt,REVEL,transcript
awk -F',' '$1=="22" && $3!="" { k=$3"\t"$4"\t"$5"\t"$8; if (!seen[k]++) print "22\t"k }' \
  revel_with_transcript_ids | sort -k2,2n | bgzip > revel_chr22.tsv.gz
tabix -s 1 -b 2 -e 2 revel_chr22.tsv.gz

echo "==> sanity: a chr22 REVEL record"
tabix revel_chr22.tsv.gz 22:23000000-23100000 | head -1

echo "==> uploading to s3://$BUCKET/revel/"
aws s3 cp revel_chr22.tsv.gz     "s3://$BUCKET/revel/revel_chr22.tsv.gz"
aws s3 cp revel_chr22.tsv.gz.tbi "s3://$BUCKET/revel/revel_chr22.tsv.gz.tbi"

echo "==> cleaning up the 6 GB source to save EBS"
rm -f revel_with_transcript_ids revel.zip
echo "==> done. Restart the service to load REVEL_PATH."
