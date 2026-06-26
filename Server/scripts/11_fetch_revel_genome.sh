#!/usr/bin/env bash
# Genome-wide REVEL missense scores (GRCh38), all chromosomes, tabix-indexed -> S3.
set -euo pipefail

BUCKET="${S3_BUCKET:-indian-genomics-data}"
DATA="$HOME/data"; cd "$DATA"

if [ ! -f revel_with_transcript_ids ]; then
  wget -q -O revel.zip "https://zenodo.org/record/7072866/files/revel-v1.3_all_chromosomes.zip"
  unzip -o revel.zip
fi

echo "==> extract all chromosomes (GRCh38 pos), dedup across transcripts"
# CSV: chr,hg19_pos,grch38_pos,ref,alt,aaref,aaalt,REVEL,transcript
# Dedup with an external (disk-backed, memory-bounded) sort rather than an awk hash
# — the genome-wide key set is ~80M entries and an in-memory hash OOMs the box.
mkdir -p "$DATA/tmp"
awk -F',' '$3 ~ /^[0-9]+$/ { print $1"\t"$3"\t"$4"\t"$5"\t"$8 }' revel_with_transcript_ids \
  | sort -S 500M -T "$DATA/tmp" -k1,1 -k2,2n -k3,3 -k4,4 -k5,5 -u \
  | bgzip > revel_genome.tsv.gz
tabix -s 1 -b 2 -e 2 revel_genome.tsv.gz
rm -rf "$DATA/tmp"

echo "==> upload to S3"
aws s3 cp revel_genome.tsv.gz     "s3://$BUCKET/revel/revel_genome.tsv.gz"
aws s3 cp revel_genome.tsv.gz.tbi "s3://$BUCKET/revel/revel_genome.tsv.gz.tbi"
rm -f revel_with_transcript_ids revel.zip
echo "DONE revel genome-wide"
