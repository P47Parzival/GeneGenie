# GeneGenie — Server (genomic annotation backend)

Genomic interpretation & risk prediction backend. ClinVar/dbSNP reference data
lives in **S3** (warehouse) and is pulled onto **EBS** (workbench) where a FastAPI
service annotates user VCFs.

```
S3 (warehouse)  ->  EC2 EBS (workbench)  ->  annotation  ->  results (SQLite -> Postgres)
```

## Current deployment

- **EC2**: Ubuntu 26.04, t3.large, 100 GB EBS, region ap-south-1, Elastic IP `3.6.214.176`
- **S3 bucket**: `indian-genomics-data`
  - `clinvar/clinvar.vcf.gz` (+ .tbi) — full ClinVar GRCh38
  - `dbsnp/dbsnp_chr22.vcf.gz` (+ .tbi) — dbSNP chr22 subset (~16.1M variants)
  - `gnomad/gnomad_exomes_chr22.vcf.bgz` (+ .tbi) — gnomAD v4.1 exomes chr22 (~4.8 GB), for AF / AF_sas
  - `onekg/onekg_sas_chr22.vcf.gz` (+ .tbi) — 1000G chr22 sites-only (~12 MB), for AF / SAS_AF
- **Service**: runs under systemd as `genegenie.service` on port 8000
- S3 access via the instance IAM role `genomics-ec2-s3-role` (no keys on the box)
- VCF region queries use the system `tabix` CLI (htslib) — no compiled Python
  bindings, so it works on the box's Python 3.14.

## Layout

```
app/
  main.py           routes: /health, /annotate, /annotate/variant
  clinvar.py        tabix-indexed ClinVar lookup (+ dbSNP/gnomAD enrich, + ACMG)
  dbsnp.py          tabix-indexed dbSNP rsID lookup (RefSeq accession mapping)
  gnomad.py         tabix-indexed gnomAD population frequencies (AF, AF_sas)
  onekg.py          tabix-indexed 1000G SAS frequencies (AF, SAS_AF)
  population.py     Indian population layer: SAS-vs-global comparison signal
  acmg.py           ACMG/AMP classification engine (PM2/BA1/BS1 + ClinVar evidence)
  pgx.py            pharmacogenomics engine (diplotype -> phenotype -> drug)
  pgx_data.py       curated CPIC knowledge base (GRCh38 coords verified via Ensembl)
  vcf_io.py         user VCF parser
  db.py             results persistence (SQLite now, Postgres later)
  models.py         request/response schemas
  config.py         env-driven settings
scripts/
  01_install_tools.sh       Step 3 — tabix/samtools/bcftools/aws cli
  02_fetch_clinvar.sh       Step 4 — download ClinVar -> S3
  03_fetch_dbsnp_chr22.sh   Step 5 — dbSNP chr22 subset -> S3
  05_fetch_gnomad_chr22.sh  Step 8 — gnomAD exomes chr22 (AF_sas) -> S3
  06_fetch_1000g_sas_chr22.sh  Week 6 — 1000G chr22 sites (SAS_AF) -> S3
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

- `GET  /health` — service status + whether ClinVar/dbSNP/gnomAD are loaded
- `GET  /stats` — portal dashboard aggregates (annotations DB + reference status)
- `POST /annotate/variant` — JSON `{chrom,pos,ref,alt}` -> annotation (incl. ACMG)
- `POST /annotate` — multipart upload of a `.vcf` -> annotations (persisted)
- `POST /pgx` — multipart `.vcf` -> pharmacogenomics report (diplotype/phenotype/drug)

Example response:

```json
{ "gene": "BRCA1", "variant": "rs80357336",
  "significance": "Pathogenic", "disease": "Familial cancer of breast", "matched": true }
```

If a variant isn't in ClinVar but falls in a loaded dbSNP subset (chr22), the
response still carries its `variant` rsID with `matched: false`. When the variant
falls in the loaded gnomAD subset (chr22), the response also carries
`global_freq` (AF) and `south_asian_freq` (AF_sas).

### ACMG classification (`acmg.py`)

Every annotation includes an ACMG/AMP call: `acmg_classification` (5-tier),
`acmg_basis` (how it was derived), and `acmg_evidence` (applied criteria).
Only criteria we can honestly evidence today are implemented:

- **PM2_Supporting** — rare/absent in gnomAD (ClinGen-downgraded to Supporting)
- **BS1** — AF ≥ 1%; **BA1** — AF ≥ 5% (stand-alone benign)
- **PP5 / BP6** — ClinVar asserts pathogenic/benign, strength scaled by review stars

A reviewed ClinVar assertion (≥1★, non-conflicting) is used as the headline
classification; otherwise the computed ACMG call stands. Because the criteria set
is small, many novel variants resolve to *Uncertain Significance* — the correct,
honest outcome. TODO: PP3/BP4 (REVEL/CADD/AlphaMissense), PVS1, PS1/PM5.

### Pharmacogenomics (`pgx.py`, `pgx_data.py`)

`POST /pgx` takes a VCF and returns per-gene star-allele diplotypes, CPIC
metabolizer phenotypes, and drug guidance for a curated subset: **CYP2C19**
(clopidogrel), **TPMT** (thiopurines), **DPYD** (fluoropyrimidines), **SLCO1B1**
(statins). GRCh38 coordinates + forward-strand REF/ALT were verified via the
Ensembl REST API. Honest simplifications: unphased genotypes, reference (*1)
assumed where a defining variant is absent, no CNV/structural alleles. Zygosity
is read from the VCF `GT` field (homozygous → 2 copies). Deferred: CYP2D6 (CNV),
warfarin (CYP2C9+VKORC1 algorithm).

### Indian population layer (`onekg.py`, `population.py`)

Adds **1000 Genomes SAS** (South Asian) as a second, independent South-Asian
frequency source alongside gnomAD `AF_sas`. `population.build_context` combines
both and emits a `population` block on each annotation: best global &
South-Asian AF, per-source breakdown, and a **comparison** flag
(`population-enriched` / `population-depleted` / `concordant`) with a
plain-language note. A variant rare globally but common in South Asians is the
classic interpretation trap — global-only rarity filters may over-call it; for a
South-Asian patient it is likely benign. The ACMG engine uses the best available
South-Asian AF for BA1/BS1, and the evidence names the driving population
(e.g. "Allele frequency 27% (South Asian) ≥ 5%").

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

- Migrate results store SQLite -> RDS/Postgres (`DATABASE_URL`).
- Wire the `/portal` dashboard to real annotation stats.
- Production hardening: nginx + TLS in front of port 8000; restrict the SG once
  the frontend is hosted (currently open to the dev machine's egress CIDRs).
- Expand reference subsets beyond chr22 (more chromosomes for dbSNP/gnomAD).
