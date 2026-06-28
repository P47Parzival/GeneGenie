'use client';

import { AlertCircle, Dna, FileUp, Loader2, Search, ShieldCheck } from 'lucide-react';
import { useState } from 'react';
import SectionHeader from '../components/SectionHeader';
import { apiUrl } from '../lib/api';

interface Annotation {
  chrom: string;
  pos: number;
  ref: string;
  alt: string;
  gene: string | null;
  variant: string | null;
  significance: string | null;
  disease: string | null;
  clinvar_id: string | null;
  matched: boolean;
  global_freq: number | null;
  south_asian_freq: number | null;
  population: PopulationContext | null;
  acmg_classification: string | null;
  acmg_basis: string | null;
  acmg_evidence: EvidenceItem[];
}

interface PopulationFrequencies {
  source: string;
  global_af: number | null;
  south_asian_af: number | null;
}

interface PopulationContext {
  global_freq: number | null;
  south_asian_freq: number | null;
  sources: PopulationFrequencies[];
  comparison: string;
  note: string | null;
}

function comparisonTone(c: string): string {
  if (c === 'population-enriched') return 'border-cyan-400/50 bg-cyan-400/20 text-cyan-100';
  if (c === 'population-depleted') return 'border-purple-400/50 bg-purple-400/20 text-purple-100';
  if (c === 'concordant') return 'border-zinc-600 bg-zinc-800/60 text-zinc-300';
  return 'border-zinc-700 bg-zinc-800/40 text-zinc-500';
}

interface EvidenceItem {
  code: string;
  category: string;
  strength: string;
  description: string;
  source: string;
}

function acmgTone(cls: string | null): string {
  if (!cls) return 'border-zinc-700 bg-zinc-800/60 text-zinc-300';
  const s = cls.toLowerCase();
  if (s === 'pathogenic') return 'border-red-400/50 bg-red-400/20 text-red-100';
  if (s === 'likely pathogenic') return 'border-orange-400/50 bg-orange-400/20 text-orange-100';
  if (s === 'benign') return 'border-emerald-400/50 bg-emerald-400/20 text-emerald-100';
  if (s === 'likely benign') return 'border-teal-400/50 bg-teal-400/20 text-teal-100';
  return 'border-amber-400/40 bg-amber-400/15 text-amber-200'; // VUS
}

function formatFreq(f: number | null): string {
  if (f === null || f === undefined) return '—';
  if (f === 0) return '0';
  if (f < 0.0001) return f.toExponential(2);
  return `${(f * 100).toFixed(4)}%`;
}

function significanceTone(sig: string | null): string {
  if (!sig) return 'border-zinc-700 bg-zinc-800/60 text-zinc-300';
  const s = sig.toLowerCase();
  if (s.includes('pathogenic') && !s.includes('benign')) return 'border-red-400/40 bg-red-400/15 text-red-200';
  if (s.includes('benign')) return 'border-emerald-400/40 bg-emerald-400/15 text-emerald-200';
  if (s.includes('uncertain') || s.includes('conflicting')) return 'border-amber-400/40 bg-amber-400/15 text-amber-200';
  return 'border-cyan-400/40 bg-cyan-400/15 text-cyan-200';
}

export default function AnnotatePage() {
  return (
    <main className="flex flex-col gap-8 pb-16">
      <section className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-8 shadow-bio backdrop-blur-md">
        <p className="text-xs uppercase tracking-[0.18em] text-cyan-200/70">Annotation</p>
        <h1 className="mt-4 max-w-4xl text-5xl font-semibold tracking-normal text-white">
          Genomic interpretation &amp; risk prediction.
        </h1>
        <p className="mt-5 max-w-3xl text-lg leading-8 text-zinc-300">
          Look up a single variant or upload a VCF. Each variant is matched against ClinVar (GRCh38) to return gene,
          dbSNP rsID, clinical significance, and associated condition.
        </p>
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <SingleVariantCard />
        <VcfUploadCard />
      </div>
    </main>
  );
}

function SingleVariantCard() {
  const [chrom, setChrom] = useState('17');
  const [pos, setPos] = useState('43045711');
  const [ref, setRef] = useState('G');
  const [alt, setAlt] = useState('C');
  const [result, setResult] = useState<Annotation | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function lookup(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await fetch(apiUrl('/annotate/variant'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ chrom, pos: Number(pos), ref, alt }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? 'Lookup failed');
      setResult(data as Annotation);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Lookup failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <article className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-5 backdrop-blur-md">
      <SectionHeader icon={Search} eyebrow="Single variant" title="Variant lookup" description="GRCh38 coordinates." />
      <form onSubmit={lookup} className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Field label="Chrom" value={chrom} onChange={setChrom} placeholder="17" />
        <Field label="Position" value={pos} onChange={setPos} placeholder="43045711" />
        <Field label="Ref" value={ref} onChange={setRef} placeholder="G" />
        <Field label="Alt" value={alt} onChange={setAlt} placeholder="C" />
        <button
          type="submit"
          disabled={loading}
          className="col-span-2 mt-1 inline-flex items-center justify-center gap-2 rounded-md bg-cyan-300 px-4 py-2.5 text-sm font-semibold text-zinc-950 transition hover:bg-cyan-200 disabled:opacity-60 sm:col-span-4"
        >
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Dna className="h-4 w-4" />}
          Annotate variant
        </button>
      </form>

      {error ? <ErrorBox message={error} /> : null}
      {result ? <ResultCard annotation={result} /> : null}
    </article>
  );
}

function VcfUploadCard() {
  const [results, setResults] = useState<Annotation[] | null>(null);
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
    setResults(null);
    try {
      const body = new FormData();
      body.append('file', input.files[0]);
      const res = await fetch(apiUrl('/annotate'), { method: 'POST', body });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? 'Upload failed');
      setResults(data.annotations as Annotation[]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <article className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-5 backdrop-blur-md">
      <SectionHeader icon={FileUp} eyebrow="Batch" title="VCF upload" description="GRCh38 .vcf or .vcf.gz." />
      <form onSubmit={upload} className="mt-5 flex flex-col gap-3">
        <label className="flex cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed border-zinc-700 bg-zinc-950/50 px-4 py-8 text-center transition hover:border-cyan-400/50">
          <FileUp className="h-6 w-6 text-cyan-300" />
          <span className="mt-3 text-sm text-zinc-300">{fileName ?? 'Click to select a VCF file'}</span>
          <span className="mt-1 text-xs text-zinc-600">Large genome? Upload the bgzipped <span className="font-mono">.vcf.gz</span> — uploads much faster.</span>
          <input
            type="file"
            name="file"
            accept=".vcf,.vcf.gz,.gz,.bgz,text/plain,application/gzip"
            className="hidden"
            onChange={(e) => setFileName(e.target.files?.[0]?.name ?? null)}
          />
        </label>
        <button
          type="submit"
          disabled={loading}
          className="inline-flex items-center justify-center gap-2 rounded-md bg-cyan-300 px-4 py-2.5 text-sm font-semibold text-zinc-950 transition hover:bg-cyan-200 disabled:opacity-60"
        >
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <ShieldCheck className="h-4 w-4" />}
          Annotate file
        </button>
      </form>

      {error ? <ErrorBox message={error} /> : null}
      {results ? (
        <div className="mt-5 flex flex-col gap-3">
          <p className="text-sm text-zinc-400">{results.length} variant(s) processed</p>
          {results.map((a, i) => (
            <ResultCard key={`${a.chrom}-${a.pos}-${a.alt}-${i}`} annotation={a} />
          ))}
        </div>
      ) : null}
    </article>
  );
}

function Field({ label, value, onChange, placeholder }: { label: string; value: string; onChange: (v: string) => void; placeholder: string }) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-xs font-medium text-zinc-400">{label}</label>
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="rounded-md border border-zinc-800 bg-zinc-950/60 px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-600 focus:border-cyan-400/60 focus:outline-none focus:ring-1 focus:ring-cyan-400/60"
      />
    </div>
  );
}

function ResultCard({ annotation }: { annotation: Annotation }) {
  return (
    <div className="mt-4 rounded-lg border border-zinc-800 bg-zinc-950/60 p-4">
      <div className="flex items-center justify-between gap-3">
        <p className="font-mono text-sm text-zinc-400">
          {annotation.chrom}:{annotation.pos} {annotation.ref}&gt;{annotation.alt}
        </p>
        <span className={`rounded-md border px-2.5 py-1 text-xs font-medium ${significanceTone(annotation.significance)}`}>
          {annotation.matched ? annotation.significance ?? 'Unknown' : 'Not in ClinVar'}
        </span>
      </div>

      {annotation.matched ? (
        <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
          <Detail label="Gene" value={annotation.gene} mono />
          <Detail label="dbSNP" value={annotation.variant} mono />
          <Detail label="Condition" value={annotation.disease} className="col-span-2" />
          <Detail label="ClinVar ID" value={annotation.clinvar_id} mono />
        </div>
      ) : (
        <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
          <Detail label="dbSNP" value={annotation.variant} mono />
          <Detail label="ClinVar" value="No clinical record" />
        </div>
      )}

      {annotation.population ? <PopulationPanel population={annotation.population} /> : null}

      {annotation.acmg_classification ? (
        <div className="mt-3 border-t border-zinc-800 pt-3">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-xs uppercase tracking-wide text-zinc-500">ACMG classification</p>
              <p className="mt-0.5 text-xs text-zinc-500">{annotation.acmg_basis}</p>
            </div>
            <span className={`rounded-md border px-2.5 py-1 text-sm font-semibold ${acmgTone(annotation.acmg_classification)}`}>
              {annotation.acmg_classification}
            </span>
          </div>
          {annotation.acmg_evidence.length ? (
            <ul className="mt-3 space-y-1.5">
              {annotation.acmg_evidence.map((e) => (
                <li key={e.code} className="flex items-start gap-2 text-sm">
                  <span
                    className={`mt-0.5 rounded px-1.5 py-0.5 font-mono text-xs ${
                      e.category === 'pathogenic'
                        ? 'bg-red-400/15 text-red-200'
                        : 'bg-emerald-400/15 text-emerald-200'
                    }`}
                  >
                    {e.code}
                  </span>
                  <span className="text-zinc-300">{e.description}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-2 text-sm text-zinc-500">No ACMG criteria could be evidenced from loaded data.</p>
          )}
        </div>
      ) : null}
    </div>
  );
}

function PopulationPanel({ population }: { population: PopulationContext }) {
  const enriched = population.comparison === 'population-enriched';
  return (
    <div className="mt-3 border-t border-zinc-800 pt-3">
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs uppercase tracking-wide text-zinc-500">Population frequency</p>
        <span className={`rounded-md border px-2.5 py-1 text-xs font-medium ${comparisonTone(population.comparison)}`}>
          {population.comparison.replace('-', ' ')}
        </span>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
        <Detail label="Global AF" value={formatFreq(population.global_freq)} mono />
        <div className={`rounded-md border px-3 py-1.5 ${enriched ? 'border-cyan-400/40 bg-cyan-400/15' : 'border-cyan-400/25 bg-cyan-400/10'}`}>
          <p className="text-xs uppercase tracking-wide text-cyan-200/80">South-Asian AF</p>
          <p className="mt-1 font-mono text-cyan-100">{formatFreq(population.south_asian_freq)}</p>
        </div>
      </div>

      {population.note ? (
        <p className={`mt-3 rounded-md border p-2.5 text-xs leading-5 ${enriched ? 'border-cyan-400/30 bg-cyan-400/10 text-cyan-100' : 'border-zinc-800 bg-zinc-950/50 text-zinc-400'}`}>
          {population.note}
        </p>
      ) : null}

      {population.sources.length ? (
        <div className="mt-2 space-y-1">
          {population.sources.map((s) => (
            <p key={s.source} className="font-mono text-xs text-zinc-500">
              {s.source}: global {formatFreq(s.global_af)} · SAS {formatFreq(s.south_asian_af)}
            </p>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function Detail({ label, value, mono, className }: { label: string; value: string | null; mono?: boolean; className?: string }) {
  return (
    <div className={className}>
      <p className="text-xs uppercase tracking-wide text-zinc-500">{label}</p>
      <p className={`mt-1 text-zinc-100 ${mono ? 'font-mono' : ''}`}>{value ?? '—'}</p>
    </div>
  );
}

function ErrorBox({ message }: { message: string }) {
  return (
    <div className="mt-4 flex items-start gap-2 rounded-md border border-red-400/30 bg-red-400/10 p-3 text-sm text-red-100">
      <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
      <span>{message}</span>
    </div>
  );
}
