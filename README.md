# GeneGenie — Genomic Interpretation & Risk Prediction

GeneGenie turns a person's genetic variants (a VCF file) into clinically meaningful
interpretation: what each variant means, how it affects disease risk and drug response,
and — uniquely — how it reads against **South-Asian** population genetics rather than a
European-default reference.

This document describes the **end-to-end workflow**: where every piece of data comes
from, what format it's in, how it's prepared, and how it flows when a user runs an
analysis. It is intentionally about data and process, not code.

Reference genome assembly is **GRCh38** everywhere.

---

## 1. The big picture

```
 PUBLIC DATA SOURCES                 OUR CLOUD                       USER
 (NCBI, EBI, AWS, Zenodo,        ┌──────────────────────┐
  Reactome, CPIC/PharmGKB)       │  S3  =  "warehouse"  │      ┌──────────────┐
        │                        │  (permanent storage  │      │  Web app      │
        │  download + prepare    │   of all reference   │      │  in browser   │
        └──────────────────────► │   datasets)          │      └──────┬───────┘
                                 └─────────┬────────────┘             │ upload VCF
                                           │ pulled onto                │ (plain or gzipped)
                                           ▼                            ▼
                                 ┌──────────────────────┐      ┌──────────────┐
                                 │  EC2 + EBS disk       │ ◄──── │  Web server   │
                                 │  = "workbench"        │      │  (streams the │
                                 │  Annotation service   │ ────► │   upload up,  │
                                 │  queries reference    │      │   relays JSON │
                                 │  data by position     │      │   results)    │
                                 └──────────────────────┘      └──────────────┘
```

Two storage roles:

- **Warehouse (S3):** every reference dataset lives here permanently after it's prepared.
- **Workbench (EC2 with an attached EBS disk):** reference data is copied from the
  warehouse onto fast local disk, where the annotation service reads it. The service
  runs continuously and answers requests coming from the web app.

The browser never talks to the annotation service directly. The web server sits in
between, streaming uploads up and relaying results back. Access to the warehouse uses a
cloud identity role (no stored keys), and the workbench has a fixed network address.

---

## 2. Data sources — where everything is fetched from

| Dataset | Fetched from | Format | What it provides | Scope held | License |
|---|---|---|---|---|---|
| **ClinVar** | NCBI public FTP (ClinVar, GRCh38 release) | bgzipped VCF + index | Known clinical significance of variants, the condition(s), the gene, and the review confidence ("star" level) | Whole genome | Public domain |
| **dbSNP** | NCBI public FTP (dbSNP) | bgzipped VCF + index | The reference SNP identifier (rsID) for a position/allele | Chromosome 22 subset | Public domain |
| **gnomAD** | AWS Open Data (gnomAD, exomes, v4.1) | bgzipped VCF → slimmed to AF + AF_sas, indexed | Population allele frequencies, **including a South-Asian frequency (AF_sas)** | Genome-wide (exomes) | Open |
| **1000 Genomes** | EBI public FTP (GRCh38 phased release) | bgzipped VCF → reduced to sites-only | Per-population allele frequencies, **including South-Asian (SAS)** — a second, independent population reference | Genome-wide | Open |
| **Reactome** | Reactome public download | tab-delimited mapping | Which biological **pathways** a gene participates in | Whole genome | CC-BY 4.0 |
| **REVEL** | Zenodo deposit (REVEL v1.3) | large CSV → reduced to a small indexed table | An in-silico **pathogenicity score (0–1)** for missense variants | Genome-wide | Free, research-friendly |
| **CPIC / PharmGKB** | Published clinical guidelines, manually curated | curated tables | Gene → drug relationships, star-allele definitions, and dosing guidance | Selected pharmacogenes | Public guidelines |
| **Ensembl** | Ensembl REST web service | JSON | Used **during preparation only** to verify exact GRCh38 coordinates, alleles (and strand), and South-Asian allele frequencies for the curated pharmacogenomic and risk-score variants | n/a | Open |

A note on coverage: ClinVar, the gene knowledge graph, **and the frequency/predictor
references (gnomAD, 1000 Genomes, REVEL) are now genome-wide**. Only dbSNP is still held as
a chromosome-22 subset (its sole job is attaching a reference SNP identifier, which ClinVar
already supplies for clinically catalogued variants). A key efficiency trick made the
gnomAD expansion cheap: we only read two fields from it (AF, AF_sas), so each chromosome is
**stripped down to just those fields** — shrinking it roughly 130× (e.g. one chromosome
from 2.1 GB to 16 MB) — which is why genome-wide gnomAD ends up a few hundred megabytes
rather than the multiple terabytes its raw form would imply.

Two source-quality decisions worth highlighting:

- **South-Asian frequency is sourced twice, independently** (from gnomAD and from 1000
  Genomes) so the two can cross-check each other.
- **Pharmacogenomic and risk-score coordinates are never trusted from memory.** Several of
  those genes sit on the minus strand, where the genomic spelling of an allele differs from
  the textbook notation, so each position, allele, and South-Asian frequency was verified
  against the Ensembl reference service before being curated.

---

## 3. File formats & tools used

- **VCF (Variant Call Format):** the universal text format for genetic variants. Each row
  is a position with its reference and alternate allele; a sample column can also carry the
  **genotype** (whether the person has one or two copies of the alternate allele).
- **bgzip:** a block-compression of those text files that still allows jumping to any
  position without reading the whole file.
- **tabix index:** a small companion index for a bgzipped, position-sorted file. It is what
  makes "give me everything at chromosome X, position Y" instant, even on a multi-gigabyte
  file. Nearly every reference dataset here is stored this way.
- **Tab-delimited / CSV tables:** used for the predictor scores and the pathway mapping.
- **JSON:** used for the precomputed gene knowledge graph and for every result the service
  returns to the web app.

The recurring pattern: **store reference data as a position-sorted, block-compressed,
tabix-indexed file, then look it up by genomic coordinate.**

---

## 4. Preparing the reference data (one-time, per dataset)

Each source is downloaded onto the workbench, reshaped into the position-indexed form
above, and copied to the warehouse. The reshaping differs by source:

- **ClinVar** is used essentially as-published (already a position-indexed VCF).
- **dbSNP** is enormous, so only the chromosome-22 slice is pulled out and re-indexed
  instead of storing hundreds of gigabytes.
- **gnomAD** is taken from the cloud-hosted open copy and used as-is for the chromosome of
  interest.
- **1000 Genomes** is downloaded with full per-person genotypes, then **stripped down to
  "sites only"** — we keep the precomputed population frequencies and discard the
  individual genotypes, shrinking it dramatically.
- **REVEL** ships as one very large all-chromosomes table; the chromosome-22 missense
  scores are extracted, de-duplicated, sorted by position, and indexed into a small table.
- **Reactome** is a gene-to-pathway mapping table, joined by gene identifier.
- **Pharmacogenomic and risk-score knowledge** is curated by hand from published guidelines,
  with each variant's coordinates and frequencies verified against the Ensembl service.

After this, everything the service needs is a set of small, position-indexed files on the
workbench's local disk, mirrored in the warehouse. A single internal registry keeps track
of which datasets exist, where they live, and whether each is currently loaded.

---

## 5. What happens when a user runs an analysis

The runtime path for an uploaded VCF:

```
 user's VCF (plain or gzipped)
        │  uploaded through the web app
        ▼
 streamed up to the annotation service     ← never fully buffered; large files are fine
        │
        ▼
 read line by line (decompressed on the fly)
        │  variant coordinates extracted; for some analyses, only the
        │  handful of positions that matter are kept
        ▼
 look up each variant by position in the reference files
        │  (for a batch, this is done as a single sweep per dataset
        │   instead of one lookup per variant, so it stays fast)
        ▼
 assemble the evidence for each variant:
   • ClinVar  → known clinical meaning, condition, confidence
   • dbSNP    → reference SNP identifier
   • gnomAD + 1000 Genomes → global and South-Asian frequencies
   • REVEL    → computational damage prediction (missense only)
        ▼
 run the interpretation engines (below)
        ▼
 return structured results (JSON) to the web app
```

Because the service stores reference data on local disk and looks it up by coordinate, the
cost of an analysis scales with the *number of variants examined*, not the size of the
reference databases. The main real-world cost for a whole-genome file is simply the time to
**upload** it — which is why uploading the compressed (`.vcf.gz`) form is recommended.

---

## 6. The interpretation engines (each, end to end)

### a) Variant annotation + clinical classification

For every variant, the assembled evidence is run through an **ACMG-style classification**
engine. ACMG is the standard clinical framework: it collects individual lines of evidence
("criteria"), each with a direction (toward damaging or toward benign) and a strength, then
combines them into a five-tier verdict — **Pathogenic, Likely Pathogenic, Uncertain (VUS),
Likely Benign, Benign**.

The evidence we can currently power, and where each comes from:

- **Rarity** — from the population frequencies. Absent/very rare leans damaging; common
  (above set thresholds) is strong or stand-alone evidence of benign.
- **Known clinical assertion** — from ClinVar, with its strength scaled by the review
  confidence (more independent expert review → stronger).
- **Computational prediction** — from REVEL, mapped to the official calibrated score
  thresholds so a high score contributes "supporting / moderate / strong" damaging
  evidence and a low score contributes benign evidence.

The engine is deliberately honest: it only applies criteria it can actually back with data,
it shows every criterion it used (so a human can see *why* a verdict was reached), and where
a well-reviewed ClinVar record exists it defers to that as the headline. Many novel variants
correctly come out as "Uncertain" — that is the right answer when the evidence is genuinely
thin, not a gap to paper over.

### b) Indian population layer (the differentiator)

This sits on top of the frequency data. For each variant it combines the South-Asian
frequency from **both** population sources, compares it to the **global** frequency, and
flags whether the variant is **enriched** (commoner in South Asians), **depleted**, or
**concordant**. Crucially, the rarity evidence in the classification step uses the
South-Asian frequency — so a variant that looks rare worldwide but is common in South Asians
is correctly recognised as likely benign *for that population*, instead of being over-flagged
the way a global-only tool would.

### c) Pharmacogenomics (drug response)

This reads the **genotypes** in the VCF at a curated set of well-established
pharmacogene positions. The flow is the clinical standard:

```
genotypes at known positions → star-allele "diplotype" → metaboliser phenotype → drug guidance
```

It accounts for whether each variant is present on one or two copies, handles known cases
where one marker rides along with another, and translates the resulting allele pair into a
metaboliser status (e.g. poor / intermediate / normal / rapid). That status maps to
published prescribing guidance for the relevant drugs (for example, clopidogrel,
thiopurines, fluoropyrimidines, statins, and codeine-type opioids). It also reports how many
of the known positions were actually present in the file, so a non-result isn't mistaken for
"all normal." This engine is honest about what it cannot see from simple genotypes (such as
whole-gene deletions or duplications).

### d) Polygenic risk scores

Most common diseases aren't caused by one variant but by the combined effect of many. This
engine reads the person's genotype at a set of trait-associated positions, multiplies each
by that variant's published effect size, and sums them into a single raw score. The score on
its own is meaningless, so it is converted into a **percentile** — but against a
**South-Asian reference distribution**, derived from South-Asian allele frequencies, rather
than the usual European-derived reference. It reports how much of the model was actually
covered by the file, and is clearly framed as illustrative/educational rather than a
clinical test.

### e) Gene knowledge graph

Separately and ahead of time, the whole of ClinVar is scanned to build a per-gene summary:
which **diseases** a gene's damaging variants are linked to, and the spread of variant
classifications for that gene. This is joined with **pathway** memberships (from Reactome)
and curated **drug** relationships. The result is a compact lookup, keyed by gene symbol,
that answers "tell me everything about this gene" instantly — the basis of the gene-summary
view and the gene context shown alongside individual variants.

### f) Clinical interpretation dashboard

This is where it comes together for a human reviewer. All the annotated variants from a file
are presented as a **triage table**, sorted so the most clinically interesting float to the
top (a priority that blends the classification, whether ClinVar knows the variant, how rare
it is in South Asians, and whether the predictor flags it). The reviewer can filter the
noise — for example, "hide benign, show only variants rare in South Asians that are
Pathogenic or Uncertain." Selecting a variant opens an **evidence panel** that spells out
exactly which criteria fired and why, the ClinVar record, the global-vs-South-Asian
frequency picture, and the gene's broader disease/drug/pathway context. The reviewer can
agree or override the call, add a note, and collect variants into a patient report.

---

## 7. Honest scope & current limitations

- **Coverage:** ClinVar, the gene knowledge graph, and the frequency/predictor references
  (gnomAD, 1000 Genomes, REVEL) are genome-wide. Only dbSNP remains a chromosome-22 subset
  (a minor rsID enrichment). So the full pipeline — rarity, South-Asian context, and
  computational prediction — now runs across the whole genome.
- **Predictor:** in-silico scoring currently covers **missense** variants only, via REVEL.
  Stronger/broader predictors exist but carry non-commercial licenses and were deferred.
- **Pharmacogenomics & risk scores** use curated subsets and are framed as illustrative;
  they are decision-support, not a replacement for accredited clinical testing.
- **Classification** implements the criteria the available data can support; several ACMG
  criteria that need additional data (e.g. functional studies, gene-mechanism rules) are not
  yet included — by design, the engine never invents evidence it doesn't have.
- **Report export** is intentionally left open, because final report formats differ per
  clinical laboratory.

---

## 8. Where this is heading

The architecture is built to extend without rework: adding a new chromosome, a new
population reference, a new predictor, or a new pharmacogene is a matter of preparing one
more position-indexed dataset and registering it. The differentiator — interpreting variants
through a **South-Asian** lens — already runs through the frequency layer, the classification
engine, and the risk-score percentiles, and deepens as more population data is added.
