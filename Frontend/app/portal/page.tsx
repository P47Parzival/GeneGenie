'use client';

import { Activity, AlertCircle, Binary, Gauge, LayoutGrid, Loader2, ShieldCheck, Terminal } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import SectionHeader from '../components/SectionHeader';

interface DashboardMetrics {
  totalSequencesAnalyzed: number;
  modelConfidenceScore: number;
  processingEfficiency: number;
  activeBatchesCount: number;
}

interface SystemEvent {
  id: string;
  timestamp: string;
  level: 'info' | 'success' | 'warning' | 'error';
  message: string;
}

interface SequenceGridCell {
  id: string;
  status: 'idle' | 'active' | 'review' | 'blocked';
  label?: string;
}

interface DashboardPayload {
  metrics: DashboardMetrics | null;
  events: SystemEvent[];
  grid: SequenceGridCell[];
}

type LoadState = 'loading' | 'ready' | 'empty' | 'error';

async function fetchDashboardPayload(): Promise<DashboardPayload> {
  await new Promise((resolve) => window.setTimeout(resolve, 700));

  return {
    metrics: null,
    events: [],
    grid: [],
  };
}

export default function PortalPage() {
  const [loadState, setLoadState] = useState<LoadState>('loading');
  const [payload, setPayload] = useState<DashboardPayload | null>(null);

  useEffect(() => {
    let isMounted = true;

    fetchDashboardPayload()
      .then((data) => {
        if (!isMounted) return;
        setPayload(data);
        setLoadState(data.metrics || data.events.length || data.grid.length ? 'ready' : 'empty');
      })
      .catch(() => {
        if (!isMounted) return;
        setLoadState('error');
      });

    return () => {
      isMounted = false;
    };
  }, []);

  const hasMetrics = Boolean(payload?.metrics);
  const hasEvents = Boolean(payload?.events.length);
  const hasGrid = Boolean(payload?.grid.length);

  const metricCards = useMemo(
    () => [
      { label: 'Total Sequences Analyzed', key: 'totalSequencesAnalyzed' as const, icon: Binary, suffix: '' },
      { label: 'Model Confidence Score', key: 'modelConfidenceScore' as const, icon: ShieldCheck, suffix: '%' },
      { label: 'Processing Efficiency', key: 'processingEfficiency' as const, icon: Gauge, suffix: '%' },
      { label: 'Active Batches', key: 'activeBatchesCount' as const, icon: Activity, suffix: '' },
    ],
    [],
  );

  return (
    <main className="flex flex-col gap-6 pb-16">
      <section className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-5 shadow-bio backdrop-blur-md">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <SectionHeader
            icon={LayoutGrid}
            eyebrow="Authenticated portal"
            title="GeneGenie Operations Console"
            description="A backend-ready interface skeleton for metrics, sequence visualization, and orchestration logs."
          />
          <ConnectionBadge loadState={loadState} />
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {metricCards.map((metric) => {
          const Icon = metric.icon;
          const value = payload?.metrics?.[metric.key];
          return (
            <article key={metric.key} className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-4 backdrop-blur-md">
              <div className="flex items-start justify-between gap-3">
                <p className="text-sm text-zinc-400">{metric.label}</p>
                <Icon className="h-5 w-5 text-cyan-300" />
              </div>
              {loadState === 'loading' ? (
                <Skeleton className="mt-4 h-8 w-24" />
              ) : hasMetrics && typeof value === 'number' ? (
                <p className="mt-4 text-3xl font-semibold text-white">
                  {value.toLocaleString()}
                  {metric.suffix}
                </p>
              ) : (
                <EmptyInline message="Awaiting API data" />
              )}
            </article>
          );
        })}
      </section>

      <section className="grid gap-4 lg:grid-cols-[1.15fr_0.85fr]">
        <article className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-5 backdrop-blur-md">
          <SectionHeader
            icon={LayoutGrid}
            eyebrow="Sequence grid"
            title="Visualizer"
            description="Grid cells render from SequenceGridCell records when the backend provides indexed sequence regions."
          />
          <div className="mt-5 rounded-lg border border-zinc-800 bg-zinc-950/70 p-4">
            {loadState === 'loading' ? (
              <div className="grid grid-cols-12 gap-1">
                {Array.from({ length: 96 }).map((_, index) => (
                  <Skeleton key={index} className="h-7 rounded-sm" />
                ))}
              </div>
            ) : hasGrid ? (
              <div className="grid grid-cols-12 gap-1">
                {payload?.grid.map((cell) => <SequenceCell key={cell.id} cell={cell} />)}
              </div>
            ) : (
              <EmptyPanel
                title="No sequence regions loaded"
                description="Connect a sequence index endpoint to populate the visualizer with real cell status records."
              />
            )}
          </div>
        </article>

        <article className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-5 backdrop-blur-md">
          <SectionHeader
            icon={Terminal}
            eyebrow="System events"
            title="Live Logs"
            description="Event rows are ready for a streaming log or polling API integration."
          />
          <div className="mt-5 h-80 overflow-hidden rounded-lg border border-zinc-800 bg-black/70">
            <div className="border-b border-zinc-800 px-4 py-3 font-mono text-xs text-zinc-500">event stream</div>
            <div className="h-full p-4 font-mono text-xs">
              {loadState === 'loading' ? (
                <div className="space-y-3">
                  <Skeleton className="h-4 w-11/12" />
                  <Skeleton className="h-4 w-9/12" />
                  <Skeleton className="h-4 w-10/12" />
                </div>
              ) : hasEvents ? (
                <div className="space-y-2">
                  {payload?.events.map((event) => (
                    <p key={event.id} className={eventTone(event.level)}>
                      {event.timestamp} [{event.level.toUpperCase()}] {event.message}
                    </p>
                  ))}
                </div>
              ) : (
                <EmptyPanel
                  title="No events available"
                  description="Connect the orchestration event stream to show real workflow activity."
                />
              )}
            </div>
          </div>
        </article>
      </section>

      {loadState === 'error' ? (
        <div className="rounded-lg border border-red-400/30 bg-red-400/10 p-4 text-sm text-red-100">
          Dashboard data could not be loaded from the configured adapter.
        </div>
      ) : null}
    </main>
  );
}

function ConnectionBadge({ loadState }: { loadState: LoadState }) {
  const copy = {
    loading: 'Loading API state',
    ready: 'Data connected',
    empty: 'No data connected',
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

function SequenceCell({ cell }: { cell: SequenceGridCell }) {
  const statusClass = {
    idle: 'border-zinc-800 bg-zinc-900',
    active: 'border-cyan-300/40 bg-cyan-400/25',
    review: 'border-amber-300/40 bg-amber-400/20',
    blocked: 'border-red-300/40 bg-red-400/20',
  }[cell.status];

  return <span title={cell.label ?? cell.id} className={`h-7 rounded-sm border ${statusClass}`} />;
}

function eventTone(level: SystemEvent['level']) {
  return {
    info: 'text-zinc-400',
    success: 'text-emerald-300',
    warning: 'text-amber-300',
    error: 'text-red-300',
  }[level];
}
