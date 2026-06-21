# GeneGenie — Server (genomic annotation backend)

Genomic interpretation & risk prediction backend. ClinVar/dbSNP reference data
lives in **S3** (warehouse) and is pulled onto **EBS** (workbench) where a FastAPI
service annotates user VCFs.

```
S3 (warehouse)  ->  EC2 EBS (workbench)  ->  annotation  ->  results (SQLite -> Postgres)
```

## Current deployment

- **EC2**: Ubuntu 26.04, t3.large, 100 GB EBS, region ap-south-1
- **S3 bucket**: `indian-genomics-data`
  - `clinvar/clinvar.vcf.gz` (+ .tbi) — full ClinVar GRCh38
  - `dbsnp/dbsnp_chr22.vcf.gz` (+ .tbi) — dbSNP chr22 subset (~16.1M variants)
- **Service**: runs under systemd as `genegenie.service` on port 8000
- S3 access via the instance IAM role `genomics-ec2-s3-role` (no keys on the box)
- VCF region queries use the system `tabix` CLI (htslib) — no compiled Python
  bindings, so it works on the box's Python 3.14.

## Layout

```
app/
  main.py           routes: /health, /annotate, /annotate/variant
  clinvar.py        tabix-indexed ClinVar lookup (+ dbSNP rsID fallback)
  dbsnp.py          tabix-indexed dbSNP rsID lookup (RefSeq accession mapping)
  vcf_io.py         user VCF parser
  db.py             results persistence (SQLite now, Postgres later)
  models.py         request/response schemas
  config.py         env-driven settings
scripts/
  01_install_tools.sh       Step 3 — tabix/samtools/bcftools/aws cli
  02_fetch_clinvar.sh       Step 4 — download ClinVar -> S3
  03_fetch_dbsnp_chr22.sh   Step 5 — dbSNP chr22 subset -> S3
  04_run_service.sh         pull ClinVar from S3 + run API (foreground)
deploy/
  genegenie.service         systemd unit (production run)
data/                       gitignored; VCFs + sqlite db (sample_user.vcf checked in)
```

## EC2 bring-up (from scratch)

```bash
bash scripts/01_install_tools.sh
S3_BUCKET=indian-genomics-data bash scripts/02_fetch_clinvar.sh
S3_BUCKET=indian-genomics-data bash scripts/03_fetch_dbsnp_chr22.sh   # optional
# install + start the service:
sudo cp deploy/genegenie.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now genegenie.service
```

Manage it: `sudo systemctl restart genegenie` · `journalctl -u genegenie -f`

## API

- `GET  /health` — service status + whether ClinVar/dbSNP are loaded
- `POST /annotate/variant` — JSON `{chrom,pos,ref,alt}` -> annotation
- `POST /annotate` — multipart upload of a `.vcf` -> annotations (persisted)

Example response:

```json
{ "gene": "BRCA1", "variant": "rs80357336",
  "significance": "Pathogenic", "disease": "Familial cancer of breast", "matched": true }
```

If a variant isn't in ClinVar but falls in a loaded dbSNP subset (chr22), the
response still carries its `variant` rsID with `matched: false`.

## Network access

The frontend reaches the API through Next.js proxy routes (`Frontend/app/api/...`).
For that to work, **port 8000 must be open** in the EC2 security group to the
caller's IP. (Production: front with nginx + TLS instead of exposing 8000.)

## Local dev

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
(`/annotate` returns 503 until a tabix-indexed `data/clinvar.vcf.gz` is present.)

## Next

- Step 8 — gnomAD chr22 with `AF_sas` (South-Asian allele frequency), the
  India-specific differentiator.
- Migrate results store SQLite -> RDS/Postgres (`DATABASE_URL`).
