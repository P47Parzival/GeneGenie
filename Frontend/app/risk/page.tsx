'use client';

import { Activity, AlertCircle, AlertTriangle, FileUp, Loader2 } from 'lucide-react';
import { useState } from 'react';
import { apiUrl } from '../lib/api';

interface PrsTraitResult {
  trait: string;
  model_id: string;
  ancestry: string;
  raw_score: number;
  reference_mean: number;
  reference_sd: number;
  z_score: number;
  percentile: number;
  risk_band: string;
  variants_total: number;
  variants_observed: number;
}

interface PrsResponse {
  results: PrsTraitResult[];
  note: string;
}

function bandTone(band: string): string {
  const s = band.toLowerCase();
  if (s.includes('high')) return 'border-red-400/50 bg-red-400/20 text-red-100';
  if (s.includes('above')) return 'border-amber-400/50 bg-amber-400/20 text-amber-100';
  if (s.includes('below')) return 'border-emerald-400/50 bg-emerald-400/20 text-emerald-100';
  return 'border-cyan-400/40 bg-cyan-400/15 text-cyan-100';
}

function barColor(percentile: number): string {
  if (percentile >= 95) return 'bg-red-400';
  if (percentile >= 80) return 'bg-amber-400';
  if (percentile < 20) return 'bg-emerald-400';
  return 'bg-cyan-400';
}

export default function RiskPage() {
  const [report, setReport] = useState<PrsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [fileName, setFileName] = useState<string | null>(null);

  async function upload(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const input = e.currentTarget.elements.namedItem('file') as HTMLInputElement;
    if (!input.files?.length) {
      setError('Choose a .vcf file first');
      return;
    }
    setLoading(true);
    setError(null);
    setReport(null);
    try {
      const body = new FormData();
      body.append('file', input.files[0]);
      const res = await fetch(apiUrl('/prs'), { method: 'POST', body });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? 'PRS analysis failed');
      setReport(data as PrsResponse);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'PRS analysis failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex flex-col gap-8 pb-16">
      <section className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-8 shadow-bio backdrop-blur-md">
        <p className="text-xs uppercase tracking-[0.18em] text-cyan-200/70">Polygenic Risk</p>
        <h1 className="mt-4 max-w-4xl text-5xl font-semibold tracking-normal text-white">
          Whole-genome risk, calibrated to South Asians.
        </h1>
        <p className="mt-5 max-w-3xl text-lg leading-8 text-zinc-300">
          Combine many variants into a single polygenic score, ranked against a South-Asian reference
          distribution rather than a European-derived one.
        </p>
        <div className="mt-5 flex items-start gap-2 rounded-md border border-amber-400/30 bg-amber-400/10 p-3 text-sm text-amber-100">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>Illustrative / educational scores — not a clinical polygenic test. See the note below results.</span>
        </div>
      </section>

      <section className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-5 backdrop-blur-md">
        <form onSubmit={upload} className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <label className="flex flex-1 cursor-pointer items-center justify-center gap-3 rounded-lg border border-dashed border-zinc-700 bg-zinc-950/50 px-4 py-6 text-center transition hover:border-cyan-400/50">
            <FileUp className="h-5 w-5 text-cyan-300" />
            <span className="text-sm text-zinc-300">{fileName ?? 'Select a VCF file'}</span>
            <input type="file" name="file" accept=".vcf,.vcf.gz,.gz,.bgz,text/plain,application/gzip" className="hidden" onChange={(e) => setFileName(e.target.files?.[0]?.name ?? null)} />
          </label>
          <button
            type="submit"
            disabled={loading}
            className="inline-flex items-center justify-center gap-2 rounded-md bg-cyan-300 px-5 py-3 text-sm font-semibold text-zinc-950 transition hover:bg-cyan-200 disabled:opacity-60"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Activity className="h-4 w-4" />}
            Compute risk
          </button>
        </form>
        {error ? (
          <div className="mt-4 flex items-start gap-2 rounded-md border border-red-400/30 bg-red-400/10 p-3 text-sm text-red-100">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        ) : null}
      </section>

      {report ? (
        <>
          <section className="grid gap-4">
            {report.results.map((r) => (
              <TraitCard key={r.model_id} result={r} />
            ))}
          </section>
          <p className="rounded-lg border border-zinc-800 bg-zinc-950/50 p-4 text-xs leading-6 text-zinc-500">{report.note}</p>
        </>
      ) : null}
    </main>
  );
}

function TraitCard({ result }: { result: PrsTraitResult }) {
  const noCoverage = result.variants_observed === 0;
  const lowCoverage = !noCoverage && result.variants_observed < result.variants_total / 2;
  return (
    <article className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-6 backdrop-blur-md">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-2xl font-semibold text-white">{result.trait}</h2>
          <p className="mt-1 text-xs text-zinc-500">{result.ancestry} · {result.model_id}</p>
        </div>
        <span className={`rounded-md border px-3 py-1.5 text-sm font-semibold ${bandTone(result.risk_band)}`}>
          {result.risk_band}
        </span>
      </div>

      {noCoverage ? (
        <div className="mt-4 flex items-start gap-2 rounded-md border border-red-400/40 bg-red-400/15 p-3 text-sm text-red-100">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>
            None of this model&apos;s {result.variants_total} variants were found in your VCF. This usually means a
            genome-build mismatch (the model uses GRCh38) or the file doesn&apos;t include these SNPs. The score below is
            just the population baseline — <strong>not meaningful for this sample</strong>.
          </span>
        </div>
      ) : lowCoverage ? (
        <div className="mt-4 flex items-start gap-2 rounded-md border border-amber-400/40 bg-amber-400/15 p-3 text-sm text-amber-100">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>
            Only {result.variants_observed} of {result.variants_total} model variants were found — limited coverage,
            interpret with caution.
          </span>
        </div>
      ) : null}

      <div className="mt-5">
        <div className="flex items-end justify-between">
          <p className="text-sm text-zinc-400">Percentile (South-Asian reference)</p>
          <p className="font-mono text-2xl font-semibold text-white">{result.percentile}</p>
        </div>
        <div className="mt-2 h-3 w-full overflow-hidden rounded-full bg-zinc-800">
          <div className={`h-full rounded-full ${barColor(result.percentile)}`} style={{ width: `${Math.min(result.percentile, 100)}%` }} />
        </div>
        <div className="mt-1 flex justify-between text-[10px] uppercase tracking-wide text-zinc-600">
          <span>lower risk</span>
          <span>average</span>
          <span>higher risk</span>
        </div>
      </div>

      <div className="mt-5 grid grid-cols-2 gap-3 border-t border-zinc-800 pt-4 text-sm sm:grid-cols-4">
        <Metric label="Raw score" value={result.raw_score.toFixed(3)} />
        <Metric label="Z-score" value={result.z_score.toFixed(2)} />
        <Metric label="Reference μ ± σ" value={`${result.reference_mean.toFixed(2)} ± ${result.reference_sd.toFixed(2)}`} />
        <Metric label="Variants genotyped" value={`${result.variants_observed} / ${result.variants_total}`} />
      </div>
    </article>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs uppercase tracking-wide text-zinc-500">{label}</p>
      <p className="mt-1 font-mono text-zinc-100">{value}</p>
    </div>
  );
}
