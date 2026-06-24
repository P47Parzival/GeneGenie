'use client';

import { AlertCircle, FileUp, Loader2, Pill } from 'lucide-react';
import { useState } from 'react';
import SectionHeader from '../components/SectionHeader';

interface PgxDrugGuidance {
  drug: string;
  recommendation: string;
  source: string;
}

interface PgxGeneResult {
  gene: string;
  diplotype: string;
  phenotype: string;
  detected: string[];
  drugs: PgxDrugGuidance[];
}

interface PgxReport {
  genes_tested: string[];
  results: PgxGeneResult[];
  note: string;
}

function phenotypeTone(phenotype: string): string {
  const s = phenotype.toLowerCase();
  if (s.includes('poor')) return 'border-red-400/50 bg-red-400/20 text-red-100';
  if (s.includes('intermediate') || s.includes('decreased')) return 'border-amber-400/50 bg-amber-400/20 text-amber-100';
  if (s.includes('rapid') || s.includes('ultrarapid')) return 'border-orange-400/50 bg-orange-400/20 text-orange-100';
  return 'border-emerald-400/50 bg-emerald-400/20 text-emerald-100'; // normal
}

function isActionable(phenotype: string): boolean {
  const s = phenotype.toLowerCase();
  return s.includes('poor') || s.includes('intermediate') || s.includes('decreased') || s.includes('ultrarapid');
}

export default function PgxPage() {
  const [report, setReport] = useState<PgxReport | null>(null);
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
      const res = await fetch('/api/pgx', { method: 'POST', body });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? 'PGx analysis failed');
      setReport(data as PgxReport);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'PGx analysis failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex flex-col gap-8 pb-16">
      <section className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-8 shadow-bio backdrop-blur-md">
        <p className="text-xs uppercase tracking-[0.18em] text-cyan-200/70">Pharmacogenomics</p>
        <h1 className="mt-4 max-w-4xl text-5xl font-semibold tracking-normal text-white">
          Drug response from the genome.
        </h1>
        <p className="mt-5 max-w-3xl text-lg leading-8 text-zinc-300">
          Upload a VCF to call star-allele diplotypes for key pharmacogenes and get CPIC-based prescribing guidance —
          CYP2C19 (clopidogrel), TPMT (thiopurines), DPYD (fluoropyrimidines), and SLCO1B1 (statins).
        </p>
      </section>

      <section className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-5 backdrop-blur-md">
        <form onSubmit={upload} className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <label className="flex flex-1 cursor-pointer items-center justify-center gap-3 rounded-lg border border-dashed border-zinc-700 bg-zinc-950/50 px-4 py-6 text-center transition hover:border-cyan-400/50">
            <FileUp className="h-5 w-5 text-cyan-300" />
            <span className="text-sm text-zinc-300">{fileName ?? 'Select a VCF file (with GT for accurate zygosity)'}</span>
            <input
              type="file"
              name="file"
              accept=".vcf,text/plain"
              className="hidden"
              onChange={(e) => setFileName(e.target.files?.[0]?.name ?? null)}
            />
          </label>
          <button
            type="submit"
            disabled={loading}
            className="inline-flex items-center justify-center gap-2 rounded-md bg-cyan-300 px-5 py-3 text-sm font-semibold text-zinc-950 transition hover:bg-cyan-200 disabled:opacity-60"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Pill className="h-4 w-4" />}
            Analyze PGx
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
          <section className="grid gap-4 md:grid-cols-2">
            {report.results.map((r) => (
              <GeneCard key={r.gene} result={r} />
            ))}
          </section>
          <p className="rounded-lg border border-zinc-800 bg-zinc-950/50 p-4 text-xs leading-6 text-zinc-500">
            {report.note}
          </p>
        </>
      ) : null}
    </main>
  );
}

function GeneCard({ result }: { result: PgxGeneResult }) {
  const actionable = isActionable(result.phenotype);
  return (
    <article
      className={`rounded-lg border bg-zinc-900/50 p-5 backdrop-blur-md ${
        actionable ? 'border-amber-400/30' : 'border-zinc-800'
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <SectionHeader icon={Pill} eyebrow="Gene" title={result.gene} description={`Diplotype ${result.diplotype}`} />
        <span className={`shrink-0 rounded-md border px-2.5 py-1 text-xs font-semibold ${phenotypeTone(result.phenotype)}`}>
          {result.phenotype}
        </span>
      </div>

      {result.detected.length ? (
        <p className="mt-4 text-xs text-zinc-500">Detected: {result.detected.join(', ')}</p>
      ) : (
        <p className="mt-4 text-xs text-zinc-500">No non-reference alleles detected (assumed *1/*1).</p>
      )}

      <div className="mt-4 space-y-3 border-t border-zinc-800 pt-4">
        {result.drugs.map((d) => (
          <div key={d.drug}>
            <div className="flex items-center justify-between">
              <p className="font-semibold capitalize text-zinc-100">{d.drug}</p>
              <span className="text-xs text-zinc-600">{d.source}</span>
            </div>
            <p className="mt-1 text-sm leading-6 text-zinc-300">{d.recommendation}</p>
          </div>
        ))}
      </div>
    </article>
  );
}
