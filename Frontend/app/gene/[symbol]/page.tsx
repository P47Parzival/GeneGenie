import { Activity, AlertTriangle, ArrowLeft, Dna, ExternalLink, Network, Pill, Workflow } from 'lucide-react';
import Link from 'next/link';
import SectionHeader from '../../components/SectionHeader';

const API_BASE = process.env.ANNOTATION_API_BASE ?? 'http://3.6.214.176:8000';

interface DiseaseAssociation { name: string; count: number }
interface DrugAssociation { drug: string; effect: string }
interface GeneVariantStats { pathogenic: number; benign: number; uncertain: number; conflicting: number; total: number }
interface GeneNode {
  symbol: string;
  ncbi_id: string | null;
  diseases: DiseaseAssociation[];
  drugs: DrugAssociation[];
  pathways: string[];
  variant_stats: GeneVariantStats;
}

export async function generateMetadata({ params }: { params: Promise<{ symbol: string }> }) {
  const { symbol } = await params;
  return { title: `${decodeURIComponent(symbol).toUpperCase()} — Gene Summary` };
}

async function fetchGene(symbol: string): Promise<GeneNode | null> {
  try {
    const res = await fetch(`${API_BASE}/gene/${encodeURIComponent(symbol.toUpperCase())}`, { cache: 'no-store' });
    if (!res.ok) return null;
    return (await res.json()) as GeneNode;
  } catch {
    return null;
  }
}

export default async function GenePage({ params }: { params: Promise<{ symbol: string }> }) {
  const { symbol } = await params;
  const gene = await fetchGene(decodeURIComponent(symbol));

  if (!gene) {
    return (
      <main className="flex flex-col gap-6 pb-16">
        <BackLink />
        <div className="flex min-h-40 flex-col items-center justify-center rounded-lg border border-dashed border-zinc-700 bg-zinc-950/40 p-10 text-center">
          <AlertTriangle className="h-6 w-6 text-amber-300" />
          <p className="mt-3 font-semibold text-zinc-200">No knowledge-graph entry for &ldquo;{decodeURIComponent(symbol).toUpperCase()}&rdquo;</p>
          <p className="mt-2 max-w-md text-sm leading-6 text-zinc-500">
            The gene may not be present in ClinVar, or the symbol may be misspelled. Try the interactive explorer.
          </p>
          <Link href="/graph" className="mt-4 text-sm text-cyan-300 hover:underline">Open knowledge graph explorer →</Link>
        </div>
      </main>
    );
  }

  return (
    <main className="flex flex-col gap-6 pb-16">
      <BackLink />

      {/* Header */}
      <section className="rounded-lg border border-cyan-400/20 bg-zinc-900/50 p-8 shadow-bio backdrop-blur-md">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="flex h-14 w-14 items-center justify-center rounded-lg border border-cyan-400/30 bg-cyan-400/10 text-cyan-300">
              <Dna className="h-7 w-7" />
            </div>
            <div>
              <p className="text-xs uppercase tracking-[0.18em] text-cyan-200/70">Gene Summary</p>
              <h1 className="mt-1 text-4xl font-semibold tracking-normal text-white">{gene.symbol}</h1>
              <p className="mt-1 text-sm text-zinc-400">
                {gene.ncbi_id ? (
                  <a className="inline-flex items-center gap-1 text-cyan-300 hover:underline" target="_blank" rel="noreferrer"
                    href={`https://www.ncbi.nlm.nih.gov/gene/${gene.ncbi_id}`}>
                    NCBI Gene {gene.ncbi_id} <ExternalLink className="h-3 w-3" />
                  </a>
                ) : 'knowledge-graph node'}
                {' · GRCh38'}
              </p>
            </div>
          </div>
          <Link href={`/graph?gene=${encodeURIComponent(gene.symbol)}`}
            className="inline-flex items-center gap-2 rounded-md border border-zinc-700 px-4 py-2 text-sm font-semibold text-zinc-100 transition hover:border-cyan-400/60 hover:text-cyan-100">
            <Network className="h-4 w-4" /> Interactive graph
          </Link>
        </div>
        <p className="mt-5 max-w-3xl text-sm leading-6 text-zinc-400">
          ClinVar variant landscape, associated conditions, drug response, and biological pathways for {gene.symbol}.
        </p>
      </section>

      <VariantDistribution stats={gene.variant_stats} />

      <div className="grid gap-4 lg:grid-cols-3">
        <DiseaseCard diseases={gene.diseases} />
        <DrugCard drugs={gene.drugs} />
        <PathwayCard pathways={gene.pathways} />
      </div>
    </main>
  );
}

function BackLink() {
  return (
    <Link href="/graph" className="inline-flex w-fit items-center gap-1.5 text-sm text-zinc-400 transition hover:text-cyan-200">
      <ArrowLeft className="h-4 w-4" /> Knowledge graph
    </Link>
  );
}

// ---------- variant distribution ----------
function VariantDistribution({ stats }: { stats: GeneVariantStats }) {
  const known = stats.pathogenic + stats.uncertain + stats.conflicting + stats.benign;
  const other = Math.max(0, stats.total - known);
  const segments = [
    { label: 'Pathogenic / Likely', value: stats.pathogenic, bar: 'bg-red-400', chip: 'border-red-400/40 bg-red-400/15 text-red-200' },
    { label: 'Uncertain (VUS)', value: stats.uncertain, bar: 'bg-amber-400', chip: 'border-amber-400/40 bg-amber-400/15 text-amber-200' },
    { label: 'Conflicting', value: stats.conflicting, bar: 'bg-purple-400', chip: 'border-purple-400/40 bg-purple-400/15 text-purple-200' },
    { label: 'Benign / Likely', value: stats.benign, bar: 'bg-emerald-400', chip: 'border-emerald-400/40 bg-emerald-400/15 text-emerald-200' },
    { label: 'Other', value: other, bar: 'bg-zinc-600', chip: 'border-zinc-700 bg-zinc-800/60 text-zinc-300' },
  ].filter((s) => s.value > 0);

  const total = stats.total || 1;
  const pct = (v: number) => ((v / total) * 100).toFixed(1);

  return (
    <section className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-6 backdrop-blur-md">
      <div className="flex items-center justify-between">
        <SectionHeader icon={Activity} eyebrow="ClinVar" title="Variant distribution" />
        <p className="text-sm text-zinc-400">{stats.total.toLocaleString()} variants</p>
      </div>

      <div className="mt-5 flex h-4 w-full overflow-hidden rounded-full bg-zinc-800">
        {segments.map((s) => (
          <div key={s.label} className={s.bar} style={{ width: `${(s.value / total) * 100}%` }} title={`${s.label}: ${s.value}`} />
        ))}
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        {segments.map((s) => (
          <div key={s.label} className={`rounded-md border px-3 py-2 ${s.chip}`}>
            <p className="text-xs opacity-80">{s.label}</p>
            <p className="mt-1 text-xl font-semibold">{s.value.toLocaleString()}</p>
            <p className="text-xs opacity-70">{pct(s.value)}%</p>
          </div>
        ))}
      </div>
    </section>
  );
}

// ---------- diseases ----------
function DiseaseCard({ diseases }: { diseases: DiseaseAssociation[] }) {
  const max = Math.max(...diseases.map((d) => d.count), 1);
  return (
    <article className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-5 backdrop-blur-md">
      <SectionHeader icon={Activity} eyebrow="ClinVar (pathogenic)" title="Associated diseases" />
      {diseases.length ? (
        <ul className="mt-4 max-h-96 space-y-2.5 overflow-auto pr-1">
          {diseases.map((d) => (
            <li key={d.name}>
              <div className="flex items-baseline justify-between gap-3">
                <span className="text-sm text-zinc-200">{d.name}</span>
                <span className="shrink-0 font-mono text-xs text-zinc-500">{d.count.toLocaleString()}</span>
              </div>
              <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-zinc-800">
                <div className="h-full rounded-full bg-cyan-400/70" style={{ width: `${(d.count / max) * 100}%` }} />
              </div>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-4 text-sm text-zinc-500">No disease associations from pathogenic variants.</p>
      )}
    </article>
  );
}

// ---------- drugs ----------
function DrugCard({ drugs }: { drugs: DrugAssociation[] }) {
  return (
    <article className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-5 backdrop-blur-md">
      <SectionHeader icon={Pill} eyebrow="CPIC / PharmGKB" title="Drug response" />
      {drugs.length ? (
        <ul className="mt-4 space-y-2.5">
          {drugs.map((d) => (
            <li key={d.drug} className="rounded-md border border-cyan-400/20 bg-cyan-400/5 px-3 py-2">
              <p className="text-sm font-semibold capitalize text-cyan-100">{d.drug}</p>
              <p className="mt-0.5 text-xs text-zinc-400">{d.effect}</p>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-4 text-sm text-zinc-500">No curated pharmacogenomic association.</p>
      )}
    </article>
  );
}

// ---------- pathways ----------
function PathwayCard({ pathways }: { pathways: string[] }) {
  return (
    <article className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-5 backdrop-blur-md">
      <SectionHeader icon={Workflow} eyebrow="Reactome" title="Pathways" />
      {pathways.length ? (
        <div className="mt-4 flex flex-wrap gap-1.5">
          {pathways.map((p) => (
            <span key={p} className="rounded border border-zinc-700 bg-zinc-950/50 px-2 py-1 text-xs text-zinc-300">{p}</span>
          ))}
        </div>
      ) : (
        <p className="mt-4 text-sm text-zinc-500">No mapped Reactome pathways.</p>
      )}
    </article>
  );
}
