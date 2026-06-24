'use client';

import { Activity, AlertCircle, Binary, Database, FlaskConical, LayoutGrid, Loader2, ShieldCheck } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import SectionHeader from '../components/SectionHeader';

interface ReferenceDatasetInfo {
  key: string;
  label: string;
  detail: string;
  category: string;
  source: string;
  genome_wide: boolean;
  loaded: boolean;
}

interface StatsMetrics {
  total_annotations: number;
  total_batches: number;
  matched_count: number;
  pathogenic_count: number;
  match_rate: number;
}

interface SignificanceBucket {
  label: string;
  count: number;
}

interface RecentVariant {
  chrom: string;
  pos: number;
  ref: string;
  alt: string;
  gene: string | null;
  variant: string | null;
  significance: string | null;
  matched: boolean;
  created_at: string;
}

interface StatsPayload {
  metrics: StatsMetrics;
  significance: SignificanceBucket[];
  recent: RecentVariant[];
}

type LoadState = 'loading' | 'ready' | 'empty' | 'error';

export default function PortalPage() {
  const [loadState, setLoadState] = useState<LoadState>('loading');
  const [payload, setPayload] = useState<StatsPayload | null>(null);
  const [datasets, setDatasets] = useState<ReferenceDatasetInfo[] | null>(null);

  useEffect(() => {
    let isMounted = true;
    Promise.all([
      fetch('/api/stats', { cache: 'no-store' }).then((r) => {
        if (!r.ok) throw new Error('stats request failed');
        return r.json();
      }),
      fetch('/api/references', { cache: 'no-store' })
        .then((r) => (r.ok ? r.json() : { datasets: [] }))
        .catch(() => ({ datasets: [] })),
    ])
      .then(([stats, refs]) => {
        if (!isMounted) return;
        setPayload(stats);
        setDatasets(refs.datasets ?? []);
        setLoadState(stats.metrics.total_annotations > 0 ? 'ready' : 'empty');
      })
      .catch(() => {
        if (!isMounted) return;
        setLoadState('error');
      });
    return () => {
      isMounted = false;
    };
  }, []);

  const metricCards = useMemo(
    () => [
      { label: 'Variants Annotated', icon: Binary, value: (m: StatsMetrics) => m.total_annotations.toLocaleString() },
      { label: 'VCF Batches', icon: LayoutGrid, value: (m: StatsMetrics) => m.total_batches.toLocaleString() },
      { label: 'ClinVar Match Rate', icon: ShieldCheck, value: (m: StatsMetrics) => `${Math.round(m.match_rate * 100)}%` },
      { label: 'Pathogenic Findings', icon: Activity, value: (m: StatsMetrics) => m.pathogenic_count.toLocaleString() },
    ],
    [],
  );

  const metrics = payload?.metrics;

  return (
    <main className="flex flex-col gap-6 pb-16">
      <section className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-5 shadow-bio backdrop-blur-md">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <SectionHeader
            icon={LayoutGrid}
            eyebrow="Authenticated portal"
            title="GeneGenie Operations Console"
            description="Live metrics from the annotation service: ClinVar, dbSNP, and gnomAD lookups."
          />
          <ConnectionBadge loadState={loadState} />
        </div>
      </section>

      <ReferencePanel datasets={datasets} loadState={loadState} />

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {metricCards.map((metric) => {
          const Icon = metric.icon;
          return (
            <article key={metric.label} className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-4 backdrop-blur-md">
              <div className="flex items-start justify-between gap-3">
                <p className="text-sm text-zinc-400">{metric.label}</p>
                <Icon className="h-5 w-5 text-cyan-300" />
              </div>
              {loadState === 'loading' ? (
                <Skeleton className="mt-4 h-8 w-24" />
              ) : metrics ? (
                <p className="mt-4 text-3xl font-semibold text-white">{metric.value(metrics)}</p>
              ) : (
                <EmptyInline message="No data yet" />
              )}
            </article>
          );
        })}
      </section>

      <section className="grid gap-4 lg:grid-cols-[0.85fr_1.15fr]">
        <article className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-5 backdrop-blur-md">
          <SectionHeader
            icon={FlaskConical}
            eyebrow="Clinical significance"
            title="Distribution"
            description="ClinVar significance across all matched variants."
          />
          <div className="mt-5">
            {loadState === 'loading' ? (
              <div className="space-y-3">
                <Skeleton className="h-6 w-full" />
                <Skeleton className="h-6 w-10/12" />
                <Skeleton className="h-6 w-8/12" />
              </div>
            ) : payload?.significance.length ? (
              <SignificanceBars buckets={payload.significance} />
            ) : (
              <EmptyPanel title="No matches yet" description="Annotate a VCF on the Annotate page to populate this." />
            )}
          </div>
        </article>

        <article className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-5 backdrop-blur-md">
          <SectionHeader
            icon={Database}
            eyebrow="Activity"
            title="Recent Variants"
            description="Most recently annotated variants across all batches."
          />
          <div className="mt-5">
            {loadState === 'loading' ? (
              <div className="space-y-2">
                <Skeleton className="h-8 w-full" />
                <Skeleton className="h-8 w-full" />
                <Skeleton className="h-8 w-11/12" />
              </div>
            ) : payload?.recent.length ? (
              <RecentTable rows={payload.recent} />
            ) : (
              <EmptyPanel title="No activity yet" description="Annotated variants will appear here." />
            )}
          </div>
        </article>
      </section>

      {loadState === 'error' ? (
        <div className="rounded-lg border border-red-400/30 bg-red-400/10 p-4 text-sm text-red-100">
          Could not reach the annotation service. Check that the API is running and port 8000 is open.
        </div>
      ) : null}
    </main>
  );
}

function ReferencePanel({ datasets, loadState }: { datasets: ReferenceDatasetInfo[] | null; loadState: LoadState }) {
  if (loadState === 'loading') {
    return (
      <section className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <article key={i} className="flex items-center justify-between rounded-lg border border-zinc-800 bg-zinc-900/50 p-4">
            <Skeleton className="h-10 w-32" />
            <Skeleton className="h-6 w-16" />
          </article>
        ))}
      </section>
    );
  }

  if (!datasets?.length) return null;

  return (
    <section className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      {datasets.map((d) => (
        <article key={d.key} className="flex items-center justify-between rounded-lg border border-zinc-800 bg-zinc-900/50 p-4 backdrop-blur-md">
          <div className="flex items-center gap-3">
            <Database className="h-5 w-5 text-cyan-300" />
            <div>
              <p className="font-semibold text-white">{d.label}</p>
              <p className="text-xs text-zinc-500">{d.detail}</p>
            </div>
          </div>
          <span
            className={`rounded-md border px-2.5 py-1 text-xs font-medium ${
              d.loaded
                ? 'border-emerald-400/40 bg-emerald-400/15 text-emerald-200'
                : 'border-zinc-700 bg-zinc-800/60 text-zinc-400'
            }`}
          >
            {d.loaded ? 'Loaded' : 'Offline'}
          </span>
        </article>
      ))}
    </section>
  );
}

function SignificanceBars({ buckets }: { buckets: SignificanceBucket[] }) {
  const max = Math.max(...buckets.map((b) => b.count), 1);
  return (
    <div className="space-y-3">
      {buckets.map((b) => (
        <div key={b.label}>
          <div className="flex items-center justify-between text-sm">
            <span className="text-zinc-300">{b.label}</span>
            <span className="font-mono text-zinc-400">{b.count}</span>
          </div>
          <div className="mt-1 h-2 overflow-hidden rounded-full bg-zinc-800">
            <div className={`h-full rounded-full ${barTone(b.label)}`} style={{ width: `${(b.count / max) * 100}%` }} />
          </div>
        </div>
      ))}
    </div>
  );
}

function RecentTable({ rows }: { rows: RecentVariant[] }) {
  return (
    <div className="overflow-hidden rounded-lg border border-zinc-800">
      <table className="w-full text-left text-sm">
        <thead className="bg-zinc-950/70 text-xs uppercase tracking-wide text-zinc-500">
          <tr>
            <th className="px-3 py-2 font-medium">Variant</th>
            <th className="px-3 py-2 font-medium">Gene</th>
            <th className="px-3 py-2 font-medium">Significance</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-800">
          {rows.map((r, i) => (
            <tr key={`${r.chrom}-${r.pos}-${r.alt}-${i}`} className="text-zinc-300">
              <td className="px-3 py-2 font-mono text-xs">
                {r.chrom}:{r.pos} {r.ref}&gt;{r.alt}
              </td>
              <td className="px-3 py-2 font-mono text-xs">{r.gene ?? '—'}</td>
              <td className="px-3 py-2">
                {r.matched ? (
                  <span className={`rounded-md border px-2 py-0.5 text-xs ${significanceTone(r.significance)}`}>
                    {r.significance ?? 'Unknown'}
                  </span>
                ) : (
                  <span className="text-xs text-zinc-600">no match</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function barTone(label: string): string {
  const s = label.toLowerCase();
  if (s.includes('pathogenic') && !s.includes('benign')) return 'bg-red-400/70';
  if (s.includes('benign')) return 'bg-emerald-400/70';
  if (s.includes('uncertain') || s.includes('conflicting')) return 'bg-amber-400/70';
  return 'bg-cyan-400/70';
}

function significanceTone(sig: string | null): string {
  if (!sig) return 'border-zinc-700 bg-zinc-800/60 text-zinc-300';
  const s = sig.toLowerCase();
  if (s.includes('pathogenic') && !s.includes('benign')) return 'border-red-400/40 bg-red-400/15 text-red-200';
  if (s.includes('benign')) return 'border-emerald-400/40 bg-emerald-400/15 text-emerald-200';
  if (s.includes('uncertain') || s.includes('conflicting')) return 'border-amber-400/40 bg-amber-400/15 text-amber-200';
  return 'border-cyan-400/40 bg-cyan-400/15 text-cyan-200';
}

function ConnectionBadge({ loadState }: { loadState: LoadState }) {
  const copy = {
    loading: 'Loading API state',
    ready: 'Data connected',
    empty: 'Connected · no data',
    error: 'Connection error',
  }[loadState];

  return (
    <div className="inline-flex items-center gap-2 rounded-md border border-cyan-400/25 bg-cyan-400/10 px-3 py-2 text-sm text-cyan-100">
      {loadState === 'loading' ? <Loader2 className="h-4 w-4 animate-spin" /> : <AlertCircle className="h-4 w-4" />}
      {copy}
    </div>
  );
}

function Skeleton({ className }: { className: string }) {
  return <div className={`animate-pulse rounded-md bg-zinc-800/80 ${className}`} />;
}

function EmptyInline({ message }: { message: string }) {
  return <p className="mt-4 rounded-md border border-zinc-800 bg-zinc-950/70 px-3 py-2 text-sm text-zinc-500">{message}</p>;
}

function EmptyPanel({ title, description }: { title: string; description: string }) {
  return (
    <div className="flex min-h-40 flex-col items-center justify-center rounded-lg border border-dashed border-zinc-700 bg-zinc-950/40 p-6 text-center">
      <p className="font-semibold text-zinc-200">{title}</p>
      <p className="mt-2 max-w-md text-sm leading-6 text-zinc-500">{description}</p>
    </div>
  );
}
