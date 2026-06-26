'use client';

import { AlertTriangle, FileUp, FlaskConical, Loader2, Star, X } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';

// ---------- types ----------
interface EvidenceItem { code: string; category: string; strength: string; description: string; source: string }
interface PopulationFrequencies { source: string; global_af: number | null; south_asian_af: number | null }
interface PopulationContext {
  global_freq: number | null;
  south_asian_freq: number | null;
  sources: PopulationFrequencies[];
  comparison: string;
  note: string | null;
}
interface Annotation {
  chrom: string; pos: number; ref: string; alt: string;
  gene: string | null; variant: string | null;
  significance: string | null; review_status: string | null; disease: string | null;
  clinvar_id: string | null; matched: boolean;
  global_freq: number | null; south_asian_freq: number | null;
  population: PopulationContext | null;
  acmg_classification: string | null; acmg_basis: string | null; acmg_evidence: EvidenceItem[];
  priority: number;
}
interface ReportItem { annotation: Annotation; userClassification: string; note: string }
interface GeneNode {
  symbol: string; ncbi_id: string | null;
  diseases: { name: string; count: number }[];
  drugs: { drug: string; effect: string }[];
  pathways: string[];
  variant_stats: { pathogenic: number; benign: number; uncertain: number; conflicting: number; total: number };
}

const ACMG_CLASSES = ['Pathogenic', 'Likely Pathogenic', 'Uncertain Significance', 'Likely Benign', 'Benign'];
const PAGE_SIZE = 100;
// Cache KG lookups so revisiting variants of the same gene doesn't refetch.
const geneCache = new Map<string, GeneNode | null>();

// ---------- helpers ----------
function vkey(a: Annotation): string { return `${a.chrom}:${a.pos}:${a.ref}>${a.alt}`; }

function acmgTone(cls: string | null): string {
  const s = (cls ?? '').toLowerCase();
  if (s === 'pathogenic') return 'border-red-400/50 bg-red-400/20 text-red-100';
  if (s === 'likely pathogenic') return 'border-orange-400/50 bg-orange-400/20 text-orange-100';
  if (s === 'benign') return 'border-emerald-400/50 bg-emerald-400/20 text-emerald-100';
  if (s === 'likely benign') return 'border-teal-400/50 bg-teal-400/20 text-teal-100';
  if (s === 'uncertain significance') return 'border-amber-400/40 bg-amber-400/15 text-amber-200';
  return 'border-zinc-700 bg-zinc-800/60 text-zinc-300';
}
function isBenign(cls: string | null): boolean {
  const s = (cls ?? '').toLowerCase();
  return s === 'benign' || s === 'likely benign';
}
function reviewStars(review: string | null): number {
  if (!review) return 0;
  const s = review.toLowerCase();
  if (s.includes('practice_guideline')) return 4;
  if (s.includes('reviewed_by_expert_panel')) return 3;
  if (s.includes('multiple_submitters') && s.includes('no_conflict')) return 2;
  if (s.includes('conflicting') || s.includes('single_submitter')) return 1;
  return 0;
}
function fmtFreq(f: number | null): string {
  if (f === null || f === undefined) return 'absent';
  if (f === 0) return '0';
  if (f < 0.0001) return f.toExponential(1);
  return `${(f * 100).toFixed(3)}%`;
}

// ---------- page ----------
export default function InterpretPage() {
  const [annotations, setAnnotations] = useState<Annotation[] | null>(null);
  const [truncated, setTruncated] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);

  // filters
  const [acmgFilter, setAcmgFilter] = useState<Set<string>>(new Set());
  const [inClinVar, setInClinVar] = useState(false);
  const [hideBenign, setHideBenign] = useState(false);
  const [maxSasAf, setMaxSasAf] = useState('');
  const [popFilter, setPopFilter] = useState('all');
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(0);

  // selection + report
  const [selected, setSelected] = useState<Annotation | null>(null);
  const [report, setReport] = useState<Record<string, ReportItem>>({});
  const [showReport, setShowReport] = useState(false);

  useEffect(() => { setPage(0); }, [acmgFilter, inClinVar, hideBenign, maxSasAf, popFilter, search]);

  async function upload(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const input = e.currentTarget.elements.namedItem('file') as HTMLInputElement;
    if (!input.files?.length) { setError('Choose a VCF file first'); return; }
    setLoading(true); setError(null); setAnnotations(null); setSelected(null);
    try {
      const body = new FormData();
      body.append('file', input.files[0]);
      const res = await fetch('/api/annotate', { method: 'POST', body });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? 'Annotation failed');
      setAnnotations(data.annotations as Annotation[]);
      setTruncated(Boolean(data.truncated));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Annotation failed');
    } finally { setLoading(false); }
  }

  const filtered = useMemo(() => {
    if (!annotations) return [];
    const maxAf = maxSasAf.trim() === '' ? null : Number(maxSasAf);
    const q = search.trim().toLowerCase();
    return annotations
      .filter((a) => {
        if (acmgFilter.size && !acmgFilter.has(a.acmg_classification ?? '')) return false;
        if (inClinVar && !a.matched) return false;
        if (hideBenign && isBenign(a.acmg_classification)) return false;
        if (maxAf !== null && !Number.isNaN(maxAf)) {
          const sas = a.south_asian_freq;
          if (!(sas === null || sas < maxAf)) return false; // absent counts as rare
        }
        if (popFilter !== 'all' && a.population?.comparison !== popFilter) return false;
        if (q) {
          const hay = `${a.gene ?? ''} ${a.variant ?? ''}`.toLowerCase();
          if (!hay.includes(q)) return false;
        }
        return true;
      })
      .sort((a, b) => b.priority - a.priority);
  }, [annotations, acmgFilter, inClinVar, hideBenign, maxSasAf, popFilter, search]);

  const pageRows = filtered.slice(page * PAGE_SIZE, page * PAGE_SIZE + PAGE_SIZE);
  const pageCount = Math.ceil(filtered.length / PAGE_SIZE);
  const reportCount = Object.keys(report).length;

  function toggleAcmg(cls: string) {
    setAcmgFilter((prev) => { const n = new Set(prev); n.has(cls) ? n.delete(cls) : n.add(cls); return n; });
  }
  function resetFilters() {
    setAcmgFilter(new Set()); setInClinVar(false); setHideBenign(false);
    setMaxSasAf(''); setPopFilter('all'); setSearch('');
  }
  function addToReport(a: Annotation, userClassification: string, note: string) {
    setReport((prev) => ({ ...prev, [vkey(a)]: { annotation: a, userClassification, note } }));
  }
  function removeFromReport(key: string) {
    setReport((prev) => { const n = { ...prev }; delete n[key]; return n; });
  }

  return (
    <main className="flex flex-col gap-5 pb-16">
      <section className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-6 shadow-bio backdrop-blur-md">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.18em] text-cyan-200/70">Interpret</p>
            <h1 className="mt-2 text-3xl font-semibold tracking-normal text-white">Variant Interpretation</h1>
          </div>
          <div className="flex items-center gap-3">
            <form onSubmit={upload} className="flex items-center gap-2">
              <label className="flex cursor-pointer items-center gap-2 rounded-md border border-dashed border-zinc-700 bg-zinc-950/50 px-3 py-2 text-sm text-zinc-300 transition hover:border-cyan-400/50">
                <FileUp className="h-4 w-4 text-cyan-300" />
                {fileName ?? 'Select VCF'}
                <input type="file" name="file" accept=".vcf,.vcf.gz,.gz,.bgz,text/plain,application/gzip" className="hidden"
                  onChange={(e) => setFileName(e.target.files?.[0]?.name ?? null)} />
              </label>
              <button type="submit" disabled={loading}
                className="inline-flex items-center gap-2 rounded-md bg-cyan-300 px-4 py-2 text-sm font-semibold text-zinc-950 transition hover:bg-cyan-200 disabled:opacity-60">
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <FlaskConical className="h-4 w-4" />}
                Annotate
              </button>
            </form>
            <button onClick={() => setShowReport(true)}
              className="inline-flex items-center gap-2 rounded-md border border-cyan-400/40 bg-cyan-400/10 px-4 py-2 text-sm font-semibold text-cyan-100 transition hover:bg-cyan-400/20">
              <Star className="h-4 w-4" /> Report ({reportCount})
            </button>
          </div>
        </div>
        <p className="mt-2 text-xs text-zinc-600">Large genome? Upload the bgzipped <span className="font-mono">.vcf.gz</span> — it&apos;s ~10× smaller and uploads much faster (a multi-GB plain .vcf can take minutes and time out).</p>
        {error ? <p className="mt-3 text-sm text-red-300">{error}</p> : null}
        {truncated ? (
          <p className="mt-3 flex items-center gap-2 rounded-md border border-amber-400/30 bg-amber-400/10 p-2 text-xs text-amber-100">
            <AlertTriangle className="h-4 w-4" /> Showing the first 10,000 variants. Upload a region/subset for full coverage.
          </p>
        ) : null}
      </section>

      {annotations ? (
        <>
          <FilterBar
            count={filtered.length} total={annotations.length}
            acmgFilter={acmgFilter} toggleAcmg={toggleAcmg}
            inClinVar={inClinVar} setInClinVar={setInClinVar}
            hideBenign={hideBenign} setHideBenign={setHideBenign}
            maxSasAf={maxSasAf} setMaxSasAf={setMaxSasAf}
            popFilter={popFilter} setPopFilter={setPopFilter}
            search={search} setSearch={setSearch} reset={resetFilters}
          />
          <TriageGrid rows={pageRows} selected={selected} onSelect={setSelected}
            inReport={(a) => Boolean(report[vkey(a)])} page={page} pageCount={pageCount} setPage={setPage} />
        </>
      ) : (
        <div className="flex min-h-40 flex-col items-center justify-center rounded-lg border border-dashed border-zinc-700 bg-zinc-950/40 p-10 text-center">
          <p className="font-semibold text-zinc-200">No VCF loaded</p>
          <p className="mt-2 max-w-md text-sm leading-6 text-zinc-500">Upload a VCF to triage its variants by ACMG classification and South-Asian frequency.</p>
        </div>
      )}

      {selected ? (
        <EvidencePanel a={selected} onClose={() => setSelected(null)}
          reportItem={report[vkey(selected)]} addToReport={addToReport} removeFromReport={() => removeFromReport(vkey(selected))} />
      ) : null}
      {showReport ? (
        <ReportDrawer report={report} onClose={() => setShowReport(false)} removeFromReport={removeFromReport} />
      ) : null}
    </main>
  );
}

// ---------- filter bar ----------
function FilterBar(p: {
  count: number; total: number;
  acmgFilter: Set<string>; toggleAcmg: (c: string) => void;
  inClinVar: boolean; setInClinVar: (b: boolean) => void;
  hideBenign: boolean; setHideBenign: (b: boolean) => void;
  maxSasAf: string; setMaxSasAf: (s: string) => void;
  popFilter: string; setPopFilter: (s: string) => void;
  search: string; setSearch: (s: string) => void; reset: () => void;
}) {
  return (
    <section className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-4 backdrop-blur-md">
      <div className="flex flex-wrap items-center gap-2">
        {ACMG_CLASSES.map((c) => (
          <button key={c} onClick={() => p.toggleAcmg(c)}
            className={`rounded-md border px-2.5 py-1 text-xs font-medium transition ${p.acmgFilter.has(c) ? acmgTone(c) : 'border-zinc-700 bg-zinc-800/40 text-zinc-400 hover:text-zinc-200'}`}>
            {c === 'Uncertain Significance' ? 'VUS' : c}
          </button>
        ))}
        <span className="mx-1 h-5 w-px bg-zinc-700" />
        <Toggle label="In ClinVar" on={p.inClinVar} set={p.setInClinVar} />
        <Toggle label="Hide benign" on={p.hideBenign} set={p.setHideBenign} />
        <div className="flex items-center gap-1.5 rounded-md border border-zinc-700 bg-zinc-950/50 px-2 py-1">
          <span className="text-xs text-zinc-400">AF_sas &lt;</span>
          <input value={p.maxSasAf} onChange={(e) => p.setMaxSasAf(e.target.value)} placeholder="0.01"
            className="w-16 bg-transparent text-xs text-zinc-100 placeholder:text-zinc-600 focus:outline-none" />
        </div>
        <select value={p.popFilter} onChange={(e) => p.setPopFilter(e.target.value)}
          className="rounded-md border border-zinc-700 bg-zinc-950/50 px-2 py-1 text-xs text-zinc-200 focus:outline-none">
          <option value="all">All populations</option>
          <option value="population-enriched">SAS-enriched</option>
          <option value="population-depleted">SAS-depleted</option>
          <option value="concordant">Concordant</option>
        </select>
        <input value={p.search} onChange={(e) => p.setSearch(e.target.value)} placeholder="gene / rsID"
          className="rounded-md border border-zinc-700 bg-zinc-950/50 px-2 py-1 text-xs text-zinc-100 placeholder:text-zinc-600 focus:outline-none" />
        <span className="ml-auto text-xs text-zinc-500">{p.count.toLocaleString()} of {p.total.toLocaleString()} shown</span>
        <button onClick={p.reset} className="text-xs text-cyan-300 hover:text-cyan-200">Reset</button>
      </div>
    </section>
  );
}
function Toggle({ label, on, set }: { label: string; on: boolean; set: (b: boolean) => void }) {
  return (
    <button onClick={() => set(!on)}
      className={`rounded-md border px-2.5 py-1 text-xs font-medium transition ${on ? 'border-cyan-400/40 bg-cyan-400/15 text-cyan-100' : 'border-zinc-700 bg-zinc-800/40 text-zinc-400 hover:text-zinc-200'}`}>
      {label}
    </button>
  );
}

// ---------- triage grid ----------
function TriageGrid(p: {
  rows: Annotation[]; selected: Annotation | null; onSelect: (a: Annotation) => void;
  inReport: (a: Annotation) => boolean; page: number; pageCount: number; setPage: (n: number) => void;
}) {
  return (
    <section className="overflow-hidden rounded-lg border border-zinc-800 bg-zinc-900/50 backdrop-blur-md">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="bg-zinc-950/70 text-xs uppercase tracking-wide text-zinc-500">
            <tr>
              <th className="px-3 py-2 font-medium"></th>
              <th className="px-3 py-2 font-medium">Variant</th>
              <th className="px-3 py-2 font-medium">Gene</th>
              <th className="px-3 py-2 font-medium">rsID</th>
              <th className="px-3 py-2 font-medium">ACMG</th>
              <th className="px-3 py-2 font-medium">ClinVar</th>
              <th className="px-3 py-2 font-medium">AF_sas</th>
              <th className="px-3 py-2 font-medium">Global AF</th>
              <th className="px-3 py-2 font-medium">Pop</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-800">
            {p.rows.map((a) => {
              const stars = reviewStars(a.review_status);
              const enriched = a.population?.comparison === 'population-enriched';
              const isSel = p.selected && vkey(p.selected) === vkey(a);
              return (
                <tr key={vkey(a)} onClick={() => p.onSelect(a)}
                  className={`cursor-pointer transition hover:bg-zinc-800/40 ${isSel ? 'bg-zinc-800/60' : ''}`}>
                  <td className="px-3 py-2">{p.inReport(a) ? <Star className="h-3.5 w-3.5 fill-cyan-300 text-cyan-300" /> : null}</td>
                  <td className="px-3 py-2 font-mono text-xs text-zinc-300">{a.chrom}:{a.pos} {a.ref}&gt;{a.alt}</td>
                  <td className="px-3 py-2 font-mono text-xs text-zinc-200">{a.gene ?? '—'}</td>
                  <td className="px-3 py-2 font-mono text-xs text-zinc-500">{a.variant ?? '—'}</td>
                  <td className="px-3 py-2">
                    <span className={`rounded border px-1.5 py-0.5 text-xs ${acmgTone(a.acmg_classification)}`}>
                      {a.acmg_classification === 'Uncertain Significance' ? 'VUS' : a.acmg_classification ?? '—'}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-xs text-zinc-400">{a.matched ? `${a.significance ?? '?'} ${'★'.repeat(stars)}` : '—'}</td>
                  <td className={`px-3 py-2 font-mono text-xs ${a.south_asian_freq === null ? 'text-zinc-600' : 'text-zinc-200'}`}>
                    {enriched ? '▲ ' : ''}{fmtFreq(a.south_asian_freq)}
                  </td>
                  <td className="px-3 py-2 font-mono text-xs text-zinc-400">{fmtFreq(a.global_freq)}</td>
                  <td className="px-3 py-2 text-xs text-zinc-500">{a.population?.comparison?.replace('population-', '') ?? '—'}</td>
                </tr>
              );
            })}
            {p.rows.length === 0 ? (
              <tr><td colSpan={9} className="px-3 py-10 text-center text-sm text-zinc-500">No variants match the current filters.</td></tr>
            ) : null}
          </tbody>
        </table>
      </div>
      {p.pageCount > 1 ? (
        <div className="flex items-center justify-between border-t border-zinc-800 px-3 py-2 text-xs text-zinc-400">
          <button disabled={p.page === 0} onClick={() => p.setPage(p.page - 1)} className="disabled:opacity-40">← Prev</button>
          <span>Page {p.page + 1} of {p.pageCount}</span>
          <button disabled={p.page >= p.pageCount - 1} onClick={() => p.setPage(p.page + 1)} className="disabled:opacity-40">Next →</button>
        </div>
      ) : null}
    </section>
  );
}

// ---------- evidence panel ----------
function EvidencePanel(p: {
  a: Annotation; onClose: () => void; reportItem?: ReportItem;
  addToReport: (a: Annotation, cls: string, note: string) => void; removeFromReport: () => void;
}) {
  const { a } = p;
  const [userClass, setUserClass] = useState(p.reportItem?.userClassification ?? a.acmg_classification ?? 'Uncertain Significance');
  const [note, setNote] = useState(p.reportItem?.note ?? '');
  const stars = reviewStars(a.review_status);
  const inReport = Boolean(p.reportItem);

  // Gene knowledge-graph context (diseases / drugs / pathways).
  const [gene, setGene] = useState<GeneNode | null | undefined>(undefined); // undefined = loading
  useEffect(() => {
    if (!a.gene) { setGene(null); return; }
    if (geneCache.has(a.gene)) { setGene(geneCache.get(a.gene) ?? null); return; }
    let active = true;
    setGene(undefined);
    fetch(`/api/gene/${encodeURIComponent(a.gene)}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((node: GeneNode | null) => { if (active) { geneCache.set(a.gene!, node); setGene(node); } })
      .catch(() => { if (active) setGene(null); });
    return () => { active = false; };
  }, [a.gene]);

  return (
    <div className="fixed inset-y-0 right-0 z-30 w-full max-w-md overflow-y-auto border-l border-zinc-800 bg-zinc-950/95 p-5 shadow-bio backdrop-blur-md">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-mono text-sm text-zinc-300">{a.chrom}:{a.pos} {a.ref}&gt;{a.alt}</p>
          <p className="mt-1 text-xs text-zinc-500">
            {a.gene ?? 'intergenic'}{a.variant ? ` · ` : ''}
            {a.variant ? <a className="text-cyan-300 hover:underline" target="_blank" rel="noreferrer"
              href={`https://www.ncbi.nlm.nih.gov/snp/${a.variant}`}>{a.variant}</a> : null}
          </p>
        </div>
        <button onClick={p.onClose} className="rounded-md p-1 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200"><X className="h-5 w-5" /></button>
      </div>

      <div className="mt-4">
        <span className={`rounded-md border px-3 py-1.5 text-sm font-semibold ${acmgTone(a.acmg_classification)}`}>
          {a.acmg_classification ?? 'Unclassified'}
        </span>
        <p className="mt-1.5 text-xs text-zinc-500">{a.acmg_basis}</p>
      </div>

      <Section title="Why">
        {a.acmg_evidence.length ? (
          <ul className="space-y-1.5">
            {a.acmg_evidence.map((e) => (
              <li key={e.code} className="flex items-start gap-2 text-sm">
                <span className={`mt-0.5 rounded px-1.5 py-0.5 font-mono text-xs ${e.category === 'pathogenic' ? 'bg-red-400/15 text-red-200' : 'bg-emerald-400/15 text-emerald-200'}`}>
                  {e.code}
                </span>
                <span className="text-zinc-300">{e.description} <span className="text-zinc-600">({e.source})</span></span>
              </li>
            ))}
          </ul>
        ) : <p className="text-sm text-zinc-500">No ACMG criteria could be evidenced from loaded data.</p>}
      </Section>

      {a.matched ? (
        <Section title="ClinVar">
          <Row label="Significance" value={`${a.significance ?? '—'} ${'★'.repeat(stars)}`} />
          <Row label="Condition" value={a.disease ?? '—'} />
          {a.clinvar_id ? (
            <a className="text-xs text-cyan-300 hover:underline" target="_blank" rel="noreferrer"
              href={`https://www.ncbi.nlm.nih.gov/clinvar/variation/${a.clinvar_id}`}>View on ClinVar →</a>
          ) : null}
        </Section>
      ) : null}

      {a.population ? (
        <Section title="Population frequency">
          <div className="grid grid-cols-2 gap-2 text-sm">
            <Row label="Global AF" value={fmtFreq(a.population.global_freq)} />
            <Row label="South-Asian AF" value={fmtFreq(a.population.south_asian_freq)} />
          </div>
          {a.population.note ? <p className="mt-2 text-xs leading-5 text-zinc-400">{a.population.note}</p> : null}
          {a.population.sources.map((s) => (
            <p key={s.source} className="mt-1 font-mono text-xs text-zinc-600">{s.source}: g {fmtFreq(s.global_af)} · SAS {fmtFreq(s.south_asian_af)}</p>
          ))}
        </Section>
      ) : null}

      {a.gene ? (
        <Section title={`Gene context · ${a.gene}`}>
          {gene === undefined ? (
            <p className="flex items-center gap-2 text-sm text-zinc-500"><Loader2 className="h-3.5 w-3.5 animate-spin" /> Loading knowledge graph…</p>
          ) : gene === null ? (
            <p className="text-sm text-zinc-500">No knowledge-graph entry for {a.gene}.</p>
          ) : (
            <div className="space-y-3">
              {gene.diseases.length ? (
                <div>
                  <p className="text-xs text-zinc-500">Associated diseases (ClinVar)</p>
                  <div className="mt-1 flex flex-wrap gap-1.5">
                    {gene.diseases.slice(0, 6).map((d) => (
                      <span key={d.name} className="rounded border border-zinc-700 bg-zinc-900/60 px-2 py-0.5 text-xs text-zinc-300">{d.name}</span>
                    ))}
                  </div>
                </div>
              ) : null}
              {gene.drugs.length ? (
                <div>
                  <p className="text-xs text-zinc-500">Drug response (CPIC/PharmGKB)</p>
                  <div className="mt-1 flex flex-wrap gap-1.5">
                    {gene.drugs.map((d) => (
                      <span key={d.drug} className="rounded border border-cyan-400/25 bg-cyan-400/10 px-2 py-0.5 text-xs capitalize text-cyan-100">{d.drug}</span>
                    ))}
                  </div>
                </div>
              ) : null}
              {gene.pathways.length ? (
                <div>
                  <p className="text-xs text-zinc-500">Pathways (Reactome)</p>
                  <div className="mt-1 flex flex-wrap gap-1.5">
                    {gene.pathways.slice(0, 5).map((pw) => (
                      <span key={pw} className="rounded border border-zinc-700 bg-zinc-900/60 px-2 py-0.5 text-xs text-zinc-400">{pw}</span>
                    ))}
                  </div>
                </div>
              ) : null}
              <a href={`/gene/${encodeURIComponent(a.gene)}`} target="_blank" rel="noreferrer" className="inline-block text-xs text-cyan-300 hover:underline">
                Open {a.gene} gene summary →
              </a>
            </div>
          )}
        </Section>
      ) : null}

      <Section title="Your call">
        <select value={userClass} onChange={(e) => setUserClass(e.target.value)}
          className="w-full rounded-md border border-zinc-700 bg-zinc-950/60 px-3 py-2 text-sm text-zinc-100 focus:outline-none">
          {ACMG_CLASSES.map((c) => <option key={c} value={c}>{c}{c === a.acmg_classification ? ' (AI)' : ''}</option>)}
        </select>
        <textarea value={note} onChange={(e) => setNote(e.target.value)} placeholder="Interpretation note (optional)"
          className="mt-2 w-full rounded-md border border-zinc-700 bg-zinc-950/60 px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-600 focus:outline-none" rows={2} />
        <div className="mt-3 flex gap-2">
          <button onClick={() => p.addToReport(a, userClass, note)}
            className="flex-1 rounded-md bg-cyan-300 px-4 py-2 text-sm font-semibold text-zinc-950 transition hover:bg-cyan-200">
            {inReport ? 'Update in report' : 'Add to patient report'}
          </button>
          {inReport ? (
            <button onClick={p.removeFromReport} className="rounded-md border border-zinc-700 px-3 py-2 text-sm text-zinc-300 hover:border-red-400/50 hover:text-red-200">Remove</button>
          ) : null}
        </div>
      </Section>
    </div>
  );
}

// ---------- report drawer ----------
function ReportDrawer(p: { report: Record<string, ReportItem>; onClose: () => void; removeFromReport: (k: string) => void }) {
  const items = Object.entries(p.report);
  function exportJson() {
    const payload = items.map(([k, it]) => ({
      variant: k, gene: it.annotation.gene, rsid: it.annotation.variant,
      ai_classification: it.annotation.acmg_classification, your_classification: it.userClassification, note: it.note,
    }));
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url; link.download = 'patient_report.json'; link.click();
    URL.revokeObjectURL(url);
  }
  return (
    <div className="fixed inset-y-0 right-0 z-40 w-full max-w-lg overflow-y-auto border-l border-zinc-800 bg-zinc-950/95 p-5 shadow-bio backdrop-blur-md">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-white">Patient Report ({items.length})</h2>
        <button onClick={p.onClose} className="rounded-md p-1 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200"><X className="h-5 w-5" /></button>
      </div>
      {items.length === 0 ? (
        <p className="mt-6 text-sm text-zinc-500">No variants added yet. Click a variant, review the evidence, and add it here.</p>
      ) : (
        <>
          <div className="mt-4 space-y-3">
            {items.map(([k, it]) => (
              <div key={k} className="rounded-md border border-zinc-800 bg-zinc-900/50 p-3">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="font-mono text-xs text-zinc-300">{k}</p>
                    <p className="text-xs text-zinc-500">{it.annotation.gene ?? '—'} {it.annotation.variant ? `· ${it.annotation.variant}` : ''}</p>
                  </div>
                  <button onClick={() => p.removeFromReport(k)} className="text-zinc-500 hover:text-red-300"><X className="h-4 w-4" /></button>
                </div>
                <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
                  <span className="text-zinc-500">AI:</span>
                  <span className={`rounded border px-1.5 py-0.5 ${acmgTone(it.annotation.acmg_classification)}`}>{it.annotation.acmg_classification ?? '—'}</span>
                  <span className="text-zinc-500">Your call:</span>
                  <span className={`rounded border px-1.5 py-0.5 ${acmgTone(it.userClassification)}`}>{it.userClassification}</span>
                </div>
                {it.note ? <p className="mt-2 text-xs leading-5 text-zinc-400">{it.note}</p> : null}
              </div>
            ))}
          </div>
          <button onClick={exportJson} className="mt-5 w-full rounded-md border border-zinc-700 px-4 py-2 text-sm font-semibold text-zinc-100 transition hover:border-cyan-400/60 hover:text-cyan-100">
            Export JSON
          </button>
          <p className="mt-2 text-center text-xs text-zinc-600">Lab-specific PDF/HTML export comes later.</p>
        </>
      )}
    </div>
  );
}

// ---------- small ui ----------
function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mt-5 border-t border-zinc-800 pt-4">
      <p className="mb-2 text-xs uppercase tracking-wide text-zinc-500">{title}</p>
      {children}
    </div>
  );
}
function Row({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-zinc-500">{label}</p>
      <p className="mt-0.5 text-sm text-zinc-200">{value}</p>
    </div>
  );
}
