'use client';

import { Activity, AlertCircle, ArrowRight, Dna, Loader2, Network, Pill, Search, Workflow } from 'lucide-react';
import Link from 'next/link';
import { useEffect, useState } from 'react';
import SectionHeader from '../components/SectionHeader';
import { apiUrl } from '../lib/api';

interface DiseaseAssociation {
  name: string;
  count: number;
}
interface DrugAssociation {
  drug: string;
  effect: string;
}
interface GeneVariantStats {
  pathogenic: number;
  benign: number;
  uncertain: number;
  conflicting: number;
  total: number;
}
interface GeneNode {
  symbol: string;
  ncbi_id: string | null;
  diseases: DiseaseAssociation[];
  drugs: DrugAssociation[];
  pathways: string[];
  variant_stats: GeneVariantStats;
}

export default function GraphPage() {
  const [query, setQuery] = useState('BRCA1');
  const [gene, setGene] = useState<GeneNode | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function runSearch(symbol: string) {
    if (!symbol) return;
    setLoading(true);
    setError(null);
    setGene(null);
    try {
      const res = await fetch(apiUrl(`/gene/${encodeURIComponent(symbol)}`));
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? 'Lookup failed');
      setGene(data as GeneNode);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Lookup failed');
    } finally {
      setLoading(false);
    }
  }

  function search(e: React.FormEvent) {
    e.preventDefault();
    runSearch(query.trim().toUpperCase());
  }

  // Honor ?gene=SYMBOL (e.g. deep-linked from the Interpret evidence panel).
  useEffect(() => {
    const param = new URLSearchParams(window.location.search).get('gene');
    if (param) {
      const symbol = param.trim().toUpperCase();
      setQuery(symbol);
      runSearch(symbol);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <main className="flex flex-col gap-8 pb-16">
      <section className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-8 shadow-bio backdrop-blur-md">
        <p className="text-xs uppercase tracking-[0.18em] text-cyan-200/70">Knowledge Graph</p>
        <h1 className="mt-4 max-w-4xl text-5xl font-semibold tracking-normal text-white">
          Gene → Disease → Drug → Pathway.
        </h1>
        <p className="mt-5 max-w-3xl text-lg leading-8 text-zinc-300">
          Explore a gene&apos;s clinical context: associated diseases (ClinVar), drug response
          (CPIC/PharmGKB), and biological pathways (Reactome).
        </p>
        <form onSubmit={search} className="mt-6 flex gap-3">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Gene symbol, e.g. BRCA1, TP53, CYP2C19"
            className="flex-1 rounded-md border border-zinc-800 bg-zinc-950/60 px-4 py-3 text-sm text-zinc-100 placeholder:text-zinc-600 focus:border-cyan-400/60 focus:outline-none focus:ring-1 focus:ring-cyan-400/60"
          />
          <button
            type="submit"
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-md bg-cyan-300 px-5 py-3 text-sm font-semibold text-zinc-950 transition hover:bg-cyan-200 disabled:opacity-60"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
            Explore
          </button>
        </form>
        {error ? (
          <div className="mt-4 flex items-start gap-2 rounded-md border border-red-400/30 bg-red-400/10 p-3 text-sm text-red-100">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        ) : null}
      </section>

      {gene ? <GeneGraph gene={gene} /> : null}
    </main>
  );
}

function GeneGraph({ gene }: { gene: GeneNode }) {
  const s = gene.variant_stats;
  return (
    <div className="flex flex-col gap-6">
      <section className="rounded-lg border border-cyan-400/20 bg-zinc-900/50 p-6 backdrop-blur-md">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-lg border border-cyan-400/30 bg-cyan-400/10 text-cyan-300">
              <Dna className="h-6 w-6" />
            </div>
            <div>
              <h2 className="text-2xl font-semibold text-white">{gene.symbol}</h2>
              <p className="text-xs text-zinc-500">{gene.ncbi_id ? `NCBI Gene ${gene.ncbi_id}` : 'gene node'}</p>
            </div>
            <Link
              href={`/gene/${encodeURIComponent(gene.symbol)}`}
              className="ml-2 inline-flex items-center gap-2 rounded-md bg-cyan-300 px-4 py-2 text-sm font-semibold text-zinc-950 transition hover:bg-cyan-200"
            >
              Gene summary <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
          <div className="flex flex-wrap gap-2 text-xs">
            <Stat label="Pathogenic" value={s.pathogenic} tone="border-red-400/40 bg-red-400/15 text-red-200" />
            <Stat label="Uncertain" value={s.uncertain} tone="border-amber-400/40 bg-amber-400/15 text-amber-200" />
            <Stat label="Benign" value={s.benign} tone="border-emerald-400/40 bg-emerald-400/15 text-emerald-200" />
            <Stat label="ClinVar total" value={s.total} tone="border-zinc-700 bg-zinc-800/60 text-zinc-300" />
          </div>
        </div>
      </section>

      <div className="grid gap-4 lg:grid-cols-3">
        <Column icon={Activity} title="Diseases" subtitle="ClinVar (pathogenic)" empty="No disease associations from pathogenic variants.">
          {gene.diseases.map((d) => (
            <li key={d.name} className="flex items-start justify-between gap-3 rounded-md border border-zinc-800 bg-zinc-950/50 px-3 py-2">
              <span className="text-sm text-zinc-200">{d.name}</span>
              <span className="shrink-0 font-mono text-xs text-zinc-500">{d.count}</span>
            </li>
          ))}
        </Column>

        <Column icon={Pill} title="Drugs" subtitle="CPIC / PharmGKB" empty="No curated pharmacogenomic association.">
          {gene.drugs.map((d) => (
            <li key={d.drug} className="rounded-md border border-zinc-800 bg-zinc-950/50 px-3 py-2">
              <p className="text-sm font-semibold capitalize text-zinc-100">{d.drug}</p>
              <p className="mt-0.5 text-xs text-zinc-400">{d.effect}</p>
            </li>
          ))}
        </Column>

        <Column icon={Workflow} title="Pathways" subtitle="Reactome" empty="No mapped Reactome pathways.">
          {gene.pathways.map((p) => (
            <li key={p} className="rounded-md border border-zinc-800 bg-zinc-950/50 px-3 py-2 text-sm text-zinc-200">
              {p}
            </li>
          ))}
        </Column>
      </div>
    </div>
  );
}

function Column({
  icon: Icon,
  title,
  subtitle,
  empty,
  children,
}: {
  icon: typeof Network;
  title: string;
  subtitle: string;
  empty: string;
  children: React.ReactNode;
}) {
  const items = Array.isArray(children) ? children : [children];
  const hasItems = items.some(Boolean) && (children as React.ReactNode[])?.length !== 0;
  return (
    <article className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-5 backdrop-blur-md">
      <SectionHeader icon={Icon} eyebrow={subtitle} title={title} />
      <ul className="mt-4 max-h-96 space-y-2 overflow-auto pr-1">
        {hasItems ? children : <p className="text-sm text-zinc-500">{empty}</p>}
      </ul>
    </article>
  );
}

function Stat({ label, value, tone }: { label: string; value: number; tone: string }) {
  return (
    <span className={`rounded-md border px-2.5 py-1 font-medium ${tone}`}>
      {label}: {value.toLocaleString()}
    </span>
  );
}
