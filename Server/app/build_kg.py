"""Build the gene knowledge-graph index (Week 4).

Aggregates a per-gene knowledge object from license-clean sources:
  - ClinVar (public domain): gene -> diseases (from P/LP variants) + variant stats
  - Reactome NCBI2Reactome (CC-BY 4.0): gene -> pathway names
  - Curated CPIC/PharmGKB gene -> drug associations (public)

Deferred (restrictive licenses): OMIM, DisGeNET.

Run on the box:
  python -m app.build_kg --clinvar ~/data/clinvar.vcf.gz \
      --reactome ~/data/NCBI2Reactome_All_Levels.txt --out ~/data/knowledge_graph.json
"""

from __future__ import annotations

import argparse
import gzip
import json
from collections import defaultdict

# Disease labels in ClinVar CLNDN that carry no clinical meaning.
SKIP_DISEASE = {
    "not provided", "not specified", "see cases", "association",
    "other", "none", "affected status unknown", "not applicable",
}

# Curated gene -> drug associations (CPIC / PharmGKB level evidence, public).
GENE_DRUGS: dict[str, list[dict]] = {
    "CYP2C19": [{"drug": "clopidogrel", "effect": "antiplatelet response"}],
    "TPMT": [{"drug": "azathioprine / mercaptopurine", "effect": "thiopurine toxicity"}],
    "DPYD": [{"drug": "fluorouracil / capecitabine", "effect": "fluoropyrimidine toxicity"}],
    "SLCO1B1": [{"drug": "simvastatin", "effect": "statin-associated myopathy"}],
    "CYP2C9": [{"drug": "warfarin", "effect": "dose requirement"}],
    "VKORC1": [{"drug": "warfarin", "effect": "dose requirement"}],
    "UGT1A1": [{"drug": "irinotecan", "effect": "toxicity"}],
    "CYP2D6": [{"drug": "codeine / tamoxifen", "effect": "metabolism / efficacy"}],
    "HLA-B": [{"drug": "abacavir / allopurinol / carbamazepine", "effect": "hypersensitivity risk"}],
    "G6PD": [{"drug": "rasburicase", "effect": "hemolysis risk"}],
}

MAX_DISEASES = 25
MAX_PATHWAYS = 25


def _parse_info(info: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for part in info.split(";"):
        key, _, value = part.partition("=")
        out[key] = value
    return out


def _sig_bucket(sig: str) -> str:
    s = sig.lower()
    if "conflicting" in s:
        return "conflicting"
    if "benign" in s:
        return "benign"
    if "pathogenic" in s:
        return "pathogenic"  # includes likely_pathogenic
    if "uncertain" in s:
        return "uncertain"
    return "other"


def build(clinvar_path: str, reactome_path: str | None, out_path: str) -> None:
    diseases: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    stats: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    gene_ncbi: dict[str, str] = {}

    print(f"scanning ClinVar: {clinvar_path}")
    with gzip.open(clinvar_path, "rt") as fh:
        for line in fh:
            if line.startswith("#"):
                continue
            cols = line.rstrip("\n").split("\t")
            if len(cols) < 8:
                continue
            info = _parse_info(cols[7])
            geneinfo = info.get("GENEINFO")
            if not geneinfo:
                continue
            gsym, _, gid = geneinfo.split("|")[0].partition(":")
            if not gsym:
                continue
            if gid:
                gene_ncbi[gsym] = gid

            sig = info.get("CLNSIG") or ""
            bucket = _sig_bucket(sig)
            stats[gsym][bucket] += 1
            stats[gsym]["total"] += 1

            if bucket == "pathogenic":
                cldn = info.get("CLNDN")
                if cldn:
                    for raw in cldn.split("|"):
                        name = raw.replace("_", " ").strip()
                        if name and name.lower() not in SKIP_DISEASE:
                            diseases[gsym][name] += 1

    print(f"  genes seen: {len(stats)}")

    gene_pathways: dict[str, set[str]] = defaultdict(set)
    if reactome_path:
        print(f"loading Reactome: {reactome_path}")
        ncbi_to_genes: dict[str, set[str]] = defaultdict(set)
        for sym, ncbi in gene_ncbi.items():
            ncbi_to_genes[ncbi].add(sym)
        with open(reactome_path) as fh:
            for line in fh:
                parts = line.rstrip("\n").split("\t")
                if len(parts) < 6 or parts[5] != "Homo sapiens":
                    continue
                ncbi_id, pathway_name = parts[0], parts[3]
                for sym in ncbi_to_genes.get(ncbi_id, ()):
                    gene_pathways[sym].add(pathway_name)
        print(f"  genes with pathways: {len(gene_pathways)}")

    genes: dict[str, dict] = {}
    for gsym, sig_counts in stats.items():
        disease_list = sorted(diseases[gsym].items(), key=lambda x: -x[1])[:MAX_DISEASES]
        pathway_list = sorted(gene_pathways.get(gsym, set()))[:MAX_PATHWAYS]
        genes[gsym] = {
            "symbol": gsym,
            "ncbi_id": gene_ncbi.get(gsym) or None,
            "diseases": [{"name": n, "count": c} for n, c in disease_list],
            "drugs": GENE_DRUGS.get(gsym, []),
            "pathways": pathway_list,
            "variant_stats": {
                "pathogenic": sig_counts.get("pathogenic", 0),
                "benign": sig_counts.get("benign", 0),
                "uncertain": sig_counts.get("uncertain", 0),
                "conflicting": sig_counts.get("conflicting", 0),
                "total": sig_counts.get("total", 0),
            },
        }

    payload = {
        "source": "ClinVar (diseases, stats) + Reactome (pathways) + curated CPIC/PharmGKB (drugs)",
        "gene_count": len(genes),
        "genes": genes,
    }
    with open(out_path, "w") as fh:
        json.dump(payload, fh)
    print(f"wrote {out_path}: {len(genes)} genes")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--clinvar", required=True)
    ap.add_argument("--reactome")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    build(args.clinvar, args.reactome, args.out)


if __name__ == "__main__":
    main()
