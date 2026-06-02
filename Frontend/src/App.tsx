import {
  Activity,
  AlertTriangle,
  BarChart3,
  Binary,
  CheckCircle2,
  Cpu,
  Dna,
  FlaskConical,
  Gauge,
  Layers3,
  Library,
  Microscope,
  Network,
  Radio,
  ScanLine,
  ShieldCheck,
  Sparkles,
  Terminal,
  Wand2,
  Zap,
} from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';

type RiskLevel = 'Safe' | 'Moderate' | 'High Risk';
type RepairMode = 'NHEJ' | 'HDR';

interface GuideCandidate {
  id: string;
  strand: string;
  start: number;
  efficiency: number;
  specificity: number;
  gcContent: number;
}

interface OffTargetLocation {
  chromosome: string;
  position: number;
  baseline: number;
}

interface ComputedOffTarget extends OffTargetLocation {
  risk: number;
  x: number;
  y: number;
}

interface MetricCard {
  label: string;
  value: string;
  delta: string;
  icon: typeof Activity;
  accent: string;
}

interface RepairResult {
  label: string;
  sequence: string;
  mutationRate: number;
  summary: string;
}

const defaultSequence =
  'ATGCGTACCGTTAAGGCTAGCTAGGATCCGATCGTAGGCTTACCGGATGCGGCTAATCGGTTAGGCTAACCGGTAGCTAGGCTAAGGTTCCGATCG';

const pamOptions = ['NGG', 'NGA', 'NNGRRT', 'TTTV'];

const offTargetBase: OffTargetLocation[] = [
  { chromosome: 'chr1', position: 12480391, baseline: 28 },
  { chromosome: 'chr4', position: 57922104, baseline: 46 },
  { chromosome: 'chr7', position: 8824021, baseline: 34 },
  { chromosome: 'chr11', position: 44190883, baseline: 57 },
  { chromosome: 'chr17', position: 76220091, baseline: 66 },
  { chromosome: 'chrX', position: 11903100, baseline: 41 },
];

const terminalEvents = [
  '[INFO] Optimizing codon usage for Homo sapiens...',
  '[SCAN] Aligning candidate gRNA against synthetic chromosome panel...',
  '[SUCCESS] Off-target risks minimized in active batch.',
  '[MODEL] Transformer confidence recalibrated with wet-lab priors.',
  '[INFO] HDR donor template normalized and indexed.',
  '[WARN] Elevated mismatch cluster detected near chr17 locus.',
  '[SUCCESS] Cas9 concentration envelope stabilized.',
  '[QUEUE] Batch GG-204 accepted for sequence analysis.',
];

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

function gcContent(sequence: string): number {
  if (!sequence.length) return 0;
  const gc = sequence.split('').filter((base) => base === 'G' || base === 'C').length;
  return Math.round((gc / sequence.length) * 100);
}

function scoreStrand(strand: string, start: number, pam: string): GuideCandidate {
  const gc = gcContent(strand);
  const pamBoost = pam === 'NGG' ? 8 : pam === 'NNGRRT' ? 5 : 3;
  const efficiency = clamp(62 + Math.round((50 - Math.abs(52 - gc)) * 0.45) + pamBoost - (start % 7), 45, 98);
  const specificity = clamp(91 - Math.round(Math.abs(48 - gc) * 0.5) - (start % 5) + pamBoost, 54, 99);

  return {
    id: `${start}-${strand.slice(0, 4)}`,
    strand,
    start,
    efficiency,
    specificity,
    gcContent: gc,
  };
}

function generateGuides(sequence: string, pam: string): GuideCandidate[] {
  const clean = sequence.toUpperCase().replace(/[^ATCG]/g, '');
  const matches: GuideCandidate[] = [];

  for (let index = 0; index <= clean.length - 23; index += 1) {
    const protospacer = clean.slice(index, index + 20);
    const pamSlice = clean.slice(index + 20, index + 23);
    const isNg = pam === 'NGG' ? pamSlice[1] === 'G' && pamSlice[2] === 'G' : pamSlice.includes('G');
    if (isNg || index % 13 === 0) {
      matches.push(scoreStrand(protospacer, index, pam));
    }
  }

  return matches
    .sort((a, b) => b.efficiency + b.specificity - (a.efficiency + a.specificity))
    .slice(0, 3);
}

function mutateNhej(sequence: string): RepairResult {
  const clean = sequence.toUpperCase().replace(/[^ATCG]/g, '');
  const cut = Math.max(12, Math.floor(clean.length / 2));
  const deletion = clean.slice(0, cut - 3) + clean.slice(cut + 2);
  const repaired = `${deletion.slice(0, cut - 3)}TGA${deletion.slice(cut - 3)}`;

  return {
    label: 'NHEJ indel outcome',
    sequence: repaired.slice(Math.max(0, cut - 22), cut + 26),
    mutationRate: 72,
    summary: 'Fast ligation pathway produced a frameshift-prone insertion and local deletion near the break site.',
  };
}

function repairHdr(sequence: string, donorTemplate: string): RepairResult {
  const clean = sequence.toUpperCase().replace(/[^ATCG]/g, '');
  const donor = donorTemplate.toUpperCase().replace(/[^ATCG]/g, '') || 'GCTTACGGAACCT';
  const cut = Math.max(12, Math.floor(clean.length / 2));
  const repaired = `${clean.slice(0, cut)}${donor}${clean.slice(cut + 8)}`;

  return {
    label: 'HDR precise insertion',
    sequence: repaired.slice(Math.max(0, cut - 18), cut + donor.length + 22),
    mutationRate: 8,
    summary: 'Template-guided repair inserted the donor cassette with clean homology-arm alignment.',
  };
}

function App() {
  const [sequence, setSequence] = useState(defaultSequence);
  const [pam, setPam] = useState('NGG');
  const [guides, setGuides] = useState<GuideCandidate[]>(generateGuides(defaultSequence, 'NGG'));
  const [scanProgress, setScanProgress] = useState(100);
  const [isScanning, setIsScanning] = useState(false);
  const [cas9, setCas9] = useState(54);
  const [tolerance, setTolerance] = useState(2);
  const [repairMode, setRepairMode] = useState<RepairMode>('NHEJ');
  const [donorTemplate, setDonorTemplate] = useState('GCTTACGGAACCTGAA');
  const [latency, setLatency] = useState(38);
  const [analyzed, setAnalyzed] = useState(12842);
  const [logs, setLogs] = useState<string[]>(terminalEvents.slice(0, 5));

  useEffect(() => {
    const timer = window.setInterval(() => {
      setLatency(28 + Math.round(Math.random() * 44));
      setAnalyzed((count) => count + Math.round(12 + Math.random() * 36));
      setLogs((current) => {
        const next = terminalEvents[Math.floor(Math.random() * terminalEvents.length)];
        const timestamp = new Date().toLocaleTimeString([], { hour12: false });
        return [...current.slice(-7), `${timestamp} ${next}`];
      });
    }, 2600);

    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    if (!isScanning) return undefined;
    setScanProgress(0);
    const timer = window.setInterval(() => {
      setScanProgress((progress) => {
        if (progress >= 100) {
          window.clearInterval(timer);
          setIsScanning(false);
          setGuides(generateGuides(sequence, pam));
          return 100;
        }
        return Math.min(100, progress + 10 + Math.round(Math.random() * 10));
      });
    }, 180);

    return () => window.clearInterval(timer);
  }, [isScanning, pam, sequence]);

  const offTargets = useMemo<ComputedOffTarget[]>(() => {
    return offTargetBase.map((site, index) => {
      const risk = clamp(site.baseline + cas9 * 0.42 + tolerance * 8 - index * 3, 4, 100);
      return {
        ...site,
        risk: Math.round(risk),
        x: 10 + index * 16,
        y: 84 - risk * 0.68,
      };
    });
  }, [cas9, tolerance]);

  const aggregateRisk = Math.round(offTargets.reduce((sum, site) => sum + site.risk, 0) / offTargets.length);
  const riskLevel: RiskLevel = aggregateRisk < 48 ? 'Safe' : aggregateRisk < 72 ? 'Moderate' : 'High Risk';
  const repairResult = repairMode === 'NHEJ' ? mutateNhej(sequence) : repairHdr(sequence, donorTemplate);
  const confidence = clamp(96 - Math.round(aggregateRisk * 0.12) + guides.length, 72, 99);

  const metrics: MetricCard[] = [
    { label: 'Total Sequences Analyzed', value: analyzed.toLocaleString(), delta: '+18.4%', icon: Binary, accent: 'text-cyan-300' },
    { label: 'Model Confidence Score', value: `${confidence}%`, delta: '+3.1%', icon: ShieldCheck, accent: 'text-emerald-300' },
    { label: 'Processing Efficiency', value: `${clamp(88 + guides.length * 2 - tolerance, 72, 99)}%`, delta: '12 ms/base', icon: Gauge, accent: 'text-teal-300' },
    { label: 'Active Batches', value: `${4 + tolerance}`, delta: '2 priority', icon: Layers3, accent: 'text-amber-300' },
  ];

  const highlightedSequence = useMemo(() => {
    const best = guides[0];
    const clean = sequence.toUpperCase().replace(/[^ATCG]/g, '');
    if (!best) return clean;
    return `${clean.slice(0, best.start)}[${clean.slice(best.start, best.start + 20)}]${clean.slice(best.start + 20)}`;
  }, [guides, sequence]);

  return (
    <main className="min-h-screen bg-zinc-950/80 text-zinc-50">
      <div className="pointer-events-none fixed inset-0 bg-data-grid bg-[length:44px_44px] opacity-40" />
      <div className="relative mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-4 sm:px-6 lg:px-8">
        <NavBar latency={latency} />

        <section id="dashboard" className="grid gap-4 lg:grid-cols-[1.18fr_0.82fr]">
          <HeroPanel confidence={confidence} aggregateRisk={aggregateRisk} />
          <AnalyticsDashboard metrics={metrics} logs={logs} />
        </section>

        <section className="grid gap-4 xl:grid-cols-[1.12fr_0.88fr]">
          <CrisprWorkspace
            sequence={sequence}
            setSequence={setSequence}
            pam={pam}
            setPam={setPam}
            guides={guides}
            highlightedSequence={highlightedSequence}
            scanProgress={scanProgress}
            isScanning={isScanning}
            onDesign={() => setIsScanning(true)}
          />
          <OffTargetPredictor
            cas9={cas9}
            setCas9={setCas9}
            tolerance={tolerance}
            setTolerance={setTolerance}
            offTargets={offTargets}
            aggregateRisk={aggregateRisk}
            riskLevel={riskLevel}
          />
        </section>

        <RepairSimulator
          sequence={sequence}
          repairMode={repairMode}
          setRepairMode={setRepairMode}
          donorTemplate={donorTemplate}
          setDonorTemplate={setDonorTemplate}
          repairResult={repairResult}
        />
      </div>
    </main>
  );
}

interface NavProps {
  latency: number;
}

function NavBar({ latency }: NavProps) {
  const links = [
    { label: 'Dashboard', href: '#dashboard' },
    { label: 'CRISPR Workspace', href: '#workspace' },
    { label: 'Off-Target Predictor', href: '#off-target' },
    { label: 'Sequence Library', href: '#library' },
  ];

  return (
    <nav className="sticky top-3 z-20 flex flex-col gap-3 rounded-lg border border-zinc-800 bg-zinc-950/80 px-4 py-3 shadow-bio backdrop-blur-md lg:flex-row lg:items-center lg:justify-between">
      <div className="flex items-center gap-3">
        <div className="flex h-11 w-11 items-center justify-center rounded-lg border border-cyan-400/30 bg-cyan-400/10 text-cyan-300">
          <Dna className="h-6 w-6" />
        </div>
        <div>
          <p className="text-lg font-semibold tracking-normal text-white">GeneGenie</p>
          <p className="text-xs uppercase tracking-[0.18em] text-cyan-200/70">AI gene-editing platform</p>
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-2 text-sm text-zinc-300">
        {links.map((link) => (
          <a key={link.href} className="rounded-md px-3 py-2 transition hover:bg-zinc-800 hover:text-cyan-200" href={link.href}>
            {link.label}
          </a>
        ))}
      </div>
      <div className="flex items-center gap-3 rounded-md border border-emerald-400/20 bg-emerald-400/10 px-3 py-2 text-sm">
        <span className="relative flex h-2.5 w-2.5">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-300 opacity-70" />
          <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-emerald-300" />
        </span>
        <span className="text-emerald-200">AI Active</span>
        <span className="text-zinc-500">|</span>
        <Radio className="h-4 w-4 text-cyan-300" />
        <span className="text-cyan-100">{latency} ms</span>
      </div>
    </nav>
  );
}

interface HeroPanelProps {
  confidence: number;
  aggregateRisk: number;
}

function HeroPanel({ confidence, aggregateRisk }: HeroPanelProps) {
  return (
    <div className="overflow-hidden rounded-lg border border-zinc-800 bg-zinc-900/50 p-5 shadow-bio backdrop-blur-md">
      <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
        <div className="max-w-2xl">
          <div className="mb-3 inline-flex items-center gap-2 rounded-md border border-cyan-400/25 bg-cyan-400/10 px-3 py-1 text-sm text-cyan-200">
            <Sparkles className="h-4 w-4" />
            Clinical-grade synthetic biology simulations
          </div>
          <h1 className="text-4xl font-semibold tracking-normal text-white sm:text-5xl">
            GeneGenie
          </h1>
          <p className="mt-3 max-w-2xl text-base leading-7 text-zinc-300">
            Design guide RNAs, stress-test off-target risk, and compare repair pathways in one live AI workspace.
          </p>
        </div>
        <div className="grid min-w-64 grid-cols-2 gap-3">
          <SignalTile label="Model Confidence" value={`${confidence}%`} tone="emerald" />
          <SignalTile label="Risk Index" value={`${aggregateRisk}`} tone={aggregateRisk > 70 ? 'red' : aggregateRisk > 48 ? 'amber' : 'cyan'} />
          <SignalTile label="gRNA Queue" value="3" tone="cyan" />
          <SignalTile label="Batches" value="Live" tone="emerald" />
        </div>
      </div>
      <div className="mt-6 grid grid-cols-12 gap-1">
        {Array.from({ length: 48 }).map((_, index) => (
          <div
            key={index}
            className={`h-8 rounded-sm border ${
              index % 7 === 0
                ? 'border-cyan-300/40 bg-cyan-400/20'
                : index % 5 === 0
                  ? 'border-emerald-300/30 bg-emerald-400/15'
                  : 'border-zinc-800 bg-zinc-950/70'
            }`}
          />
        ))}
      </div>
    </div>
  );
}

interface SignalTileProps {
  label: string;
  value: string;
  tone: 'cyan' | 'emerald' | 'amber' | 'red';
}

function SignalTile({ label, value, tone }: SignalTileProps) {
  const toneClass = {
    cyan: 'border-cyan-400/25 bg-cyan-400/10 text-cyan-200',
    emerald: 'border-emerald-400/25 bg-emerald-400/10 text-emerald-200',
    amber: 'border-amber-400/25 bg-amber-400/10 text-amber-200',
    red: 'border-red-400/25 bg-red-400/10 text-red-200',
  }[tone];

  return (
    <div className={`rounded-lg border p-4 ${toneClass}`}>
      <p className="text-xs uppercase tracking-[0.16em] opacity-70">{label}</p>
      <p className="mt-2 text-2xl font-semibold tracking-normal">{value}</p>
    </div>
  );
}

interface WorkspaceProps {
  sequence: string;
  setSequence: (value: string) => void;
  pam: string;
  setPam: (value: string) => void;
  guides: GuideCandidate[];
  highlightedSequence: string;
  scanProgress: number;
  isScanning: boolean;
  onDesign: () => void;
}

function CrisprWorkspace({
  sequence,
  setSequence,
  pam,
  setPam,
  guides,
  highlightedSequence,
  scanProgress,
  isScanning,
  onDesign,
}: WorkspaceProps) {
  return (
    <section id="workspace" className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-5 backdrop-blur-md">
      <SectionHeader icon={Wand2} eyebrow="Feature 01" title="CRISPR Workspace & gRNA Designer" />
      <div className="mt-5 grid gap-4 lg:grid-cols-[1fr_14rem]">
        <label className="block">
          <span className="mb-2 block text-sm text-zinc-300">DNA sequence input</span>
          <textarea
            value={sequence}
            onChange={(event) => setSequence(event.target.value.toUpperCase())}
            className="min-h-40 w-full resize-y rounded-lg border border-zinc-800 bg-zinc-950/80 p-4 font-mono text-sm leading-6 text-cyan-50 outline-none transition focus:border-cyan-400/70 focus:ring-2 focus:ring-cyan-400/20"
          />
        </label>
        <div className="flex flex-col gap-3">
          <label>
            <span className="mb-2 block text-sm text-zinc-300">Target PAM</span>
            <select
              value={pam}
              onChange={(event) => setPam(event.target.value)}
              className="w-full rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-3 text-zinc-100 outline-none focus:border-cyan-400/70"
            >
              {pamOptions.map((option) => (
                <option key={option}>{option}</option>
              ))}
            </select>
          </label>
          <button
            type="button"
            onClick={onDesign}
            disabled={isScanning}
            className="inline-flex items-center justify-center gap-2 rounded-lg bg-cyan-400 px-4 py-3 font-semibold text-zinc-950 transition hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-70"
          >
            <ScanLine className="h-5 w-5" />
            {isScanning ? 'Scanning' : 'Design gRNA'}
          </button>
          <div className="rounded-lg border border-zinc-800 bg-zinc-950/70 p-3">
            <div className="mb-2 flex items-center justify-between text-xs text-zinc-400">
              <span>AI scan progress</span>
              <span>{scanProgress}%</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-zinc-800">
              <div className="h-full rounded-full bg-cyan-400 transition-all duration-300" style={{ width: `${scanProgress}%` }} />
            </div>
          </div>
        </div>
      </div>
      <div className="mt-4 rounded-lg border border-cyan-400/15 bg-cyan-400/5 p-3">
        <p className="mb-2 text-xs uppercase tracking-[0.16em] text-cyan-200/70">Matched target region</p>
        <p className="break-all font-mono text-sm leading-7 text-zinc-300">
          {highlightedSequence.split(/(\[[ATCG]+\])/).map((part, index) =>
            part.startsWith('[') ? (
              <span key={index} className="rounded bg-emerald-400/20 px-1 text-emerald-200 ring-1 ring-emerald-300/30">
                {part.replace(/\[|\]/g, '')}
              </span>
            ) : (
              <span key={index}>{part}</span>
            ),
          )}
        </p>
      </div>
      <div className="mt-4 overflow-hidden rounded-lg border border-zinc-800">
        <table className="w-full min-w-[680px] text-left text-sm">
          <thead className="bg-zinc-950 text-xs uppercase tracking-[0.14em] text-zinc-400">
            <tr>
              <th className="px-4 py-3">gRNA Strand</th>
              <th className="px-4 py-3">Start</th>
              <th className="px-4 py-3">Efficiency</th>
              <th className="px-4 py-3">Specificity</th>
              <th className="px-4 py-3">GC Content</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-800 bg-zinc-950/50">
            {guides.map((guide) => (
              <tr key={guide.id} className="transition hover:bg-zinc-800/50">
                <td className="px-4 py-3 font-mono text-cyan-100">{guide.strand}</td>
                <td className="px-4 py-3 text-zinc-300">{guide.start}</td>
                <td className="px-4 py-3 text-emerald-300">{guide.efficiency}%</td>
                <td className="px-4 py-3 text-cyan-300">{guide.specificity}%</td>
                <td className="px-4 py-3 text-zinc-200">{guide.gcContent}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

interface OffTargetProps {
  cas9: number;
  setCas9: (value: number) => void;
  tolerance: number;
  setTolerance: (value: number) => void;
  offTargets: ComputedOffTarget[];
  aggregateRisk: number;
  riskLevel: RiskLevel;
}

function OffTargetPredictor({
  cas9,
  setCas9,
  tolerance,
  setTolerance,
  offTargets,
  aggregateRisk,
  riskLevel,
}: OffTargetProps) {
  const riskTone =
    riskLevel === 'Safe'
      ? 'border-emerald-400/30 bg-emerald-400/10 text-emerald-200'
      : riskLevel === 'Moderate'
        ? 'border-amber-400/30 bg-amber-400/10 text-amber-200'
        : 'border-red-400/30 bg-red-400/10 text-red-200';

  return (
    <section id="off-target" className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-5 backdrop-blur-md">
      <SectionHeader icon={Network} eyebrow="Feature 02" title="AI Off-Target Effects Predictor" />
      <div className="mt-5 grid gap-4 sm:grid-cols-2">
        <RangeControl label="Cas9 Enzyme Concentration" value={cas9} min={10} max={100} suffix="nM" onChange={setCas9} />
        <RangeControl label="Mismatch Tolerance" value={tolerance} min={1} max={5} suffix="bp" onChange={setTolerance} />
      </div>
      <div className={`mt-5 rounded-lg border p-4 ${riskTone}`}>
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-sm opacity-75">Aggregate risk score</p>
            <p className="mt-1 text-3xl font-semibold">{aggregateRisk}</p>
          </div>
          <div className="flex items-center gap-2 text-lg font-semibold">
            {riskLevel === 'High Risk' ? <AlertTriangle className="h-6 w-6" /> : <CheckCircle2 className="h-6 w-6" />}
            {riskLevel}
          </div>
        </div>
      </div>
      <div className="mt-5 rounded-lg border border-zinc-800 bg-zinc-950/70 p-4">
        <div className="mb-3 flex items-center justify-between text-sm">
          <span className="text-zinc-300">Chromosomal cleavage coordinate map</span>
          <span className="text-cyan-200">{offTargets.length} sites</span>
        </div>
        <svg viewBox="0 0 100 100" className="h-64 w-full rounded-md border border-zinc-800 bg-zinc-950">
          {[20, 40, 60, 80].map((line) => (
            <line key={line} x1="4" x2="96" y1={line} y2={line} stroke="rgba(63,63,70,0.65)" strokeWidth="0.4" />
          ))}
          <polyline
            points={offTargets.map((site) => `${site.x},${site.y}`).join(' ')}
            fill="none"
            stroke="rgb(34,211,238)"
            strokeWidth="1.2"
          />
          {offTargets.map((site) => (
            <g key={site.chromosome}>
              <circle
                cx={site.x}
                cy={site.y}
                r={3 + site.risk / 28}
                className={site.risk > 72 ? 'fill-red-400' : site.risk > 48 ? 'fill-amber-300' : 'fill-emerald-300'}
                opacity="0.8"
              />
              <text x={site.x} y="96" textAnchor="middle" className="fill-zinc-400 text-[4px]">
                {site.chromosome}
              </text>
            </g>
          ))}
        </svg>
        <div className="mt-4 grid gap-2">
          {offTargets.map((site) => (
            <div key={`${site.chromosome}-${site.position}`} className="grid grid-cols-[4.5rem_1fr_3rem] items-center gap-3 text-sm">
              <span className="font-mono text-zinc-300">{site.chromosome}</span>
              <div className="h-2 rounded-full bg-zinc-800">
                <div
                  className={`h-full rounded-full ${site.risk > 72 ? 'bg-red-400' : site.risk > 48 ? 'bg-amber-300' : 'bg-emerald-300'}`}
                  style={{ width: `${site.risk}%` }}
                />
              </div>
              <span className="text-right text-zinc-300">{site.risk}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

interface RangeControlProps {
  label: string;
  value: number;
  min: number;
  max: number;
  suffix: string;
  onChange: (value: number) => void;
}

function RangeControl({ label, value, min, max, suffix, onChange }: RangeControlProps) {
  return (
    <label className="rounded-lg border border-zinc-800 bg-zinc-950/70 p-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <span className="text-sm text-zinc-300">{label}</span>
        <span className="rounded-md bg-cyan-400/10 px-2 py-1 text-sm font-semibold text-cyan-200">
          {value} {suffix}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
        className="h-2 w-full cursor-pointer accent-cyan-400"
      />
    </label>
  );
}

interface RepairProps {
  sequence: string;
  repairMode: RepairMode;
  setRepairMode: (mode: RepairMode) => void;
  donorTemplate: string;
  setDonorTemplate: (value: string) => void;
  repairResult: RepairResult;
}

function RepairSimulator({
  sequence,
  repairMode,
  setRepairMode,
  donorTemplate,
  setDonorTemplate,
  repairResult,
}: RepairProps) {
  const cut = Math.max(12, Math.floor(sequence.replace(/[^ATCG]/gi, '').length / 2));
  const before = sequence.toUpperCase().replace(/[^ATCG]/g, '').slice(cut - 16, cut);
  const after = sequence.toUpperCase().replace(/[^ATCG]/g, '').slice(cut, cut + 16);

  return (
    <section id="library" className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-5 backdrop-blur-md">
      <SectionHeader icon={FlaskConical} eyebrow="Feature 03" title="Live Sequence Mutation & Repair Simulator" />
      <div className="mt-5 grid gap-5 lg:grid-cols-[0.8fr_1.2fr]">
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-2 rounded-lg border border-zinc-800 bg-zinc-950/70 p-2">
            {(['NHEJ', 'HDR'] as RepairMode[]).map((mode) => (
              <button
                key={mode}
                type="button"
                onClick={() => setRepairMode(mode)}
                className={`rounded-md px-3 py-3 font-semibold transition ${
                  repairMode === mode ? 'bg-emerald-400 text-zinc-950' : 'text-zinc-300 hover:bg-zinc-800'
                }`}
              >
                {mode}
              </button>
            ))}
          </div>
          {repairMode === 'HDR' && (
            <label className="block rounded-lg border border-emerald-400/20 bg-emerald-400/10 p-4">
              <span className="mb-2 block text-sm text-emerald-100">Donor Template</span>
              <input
                value={donorTemplate}
                onChange={(event) => setDonorTemplate(event.target.value.toUpperCase())}
                className="w-full rounded-md border border-emerald-300/20 bg-zinc-950 px-3 py-3 font-mono text-sm text-emerald-50 outline-none focus:border-emerald-300/70"
              />
            </label>
          )}
          <div className="rounded-lg border border-zinc-800 bg-zinc-950/70 p-4">
            <p className="text-sm text-zinc-400">Mutation rate</p>
            <p className={repairResult.mutationRate > 50 ? 'mt-1 text-4xl font-semibold text-red-300' : 'mt-1 text-4xl font-semibold text-emerald-300'}>
              {repairResult.mutationRate}%
            </p>
            <p className="mt-3 text-sm leading-6 text-zinc-300">{repairResult.summary}</p>
          </div>
        </div>
        <div className="rounded-lg border border-zinc-800 bg-zinc-950/70 p-4">
          <div className="mb-4 flex items-center gap-2 text-sm text-cyan-200">
            <Zap className="h-4 w-4" />
            Double-strand break visualization
          </div>
          <div className="grid gap-2 sm:grid-cols-[1fr_auto_1fr] sm:items-center">
            <SequenceBlock label="Left arm" sequence={before} />
            <div className="flex h-16 items-center justify-center">
              <div className="flex h-14 w-14 items-center justify-center rounded-full border border-red-400/40 bg-red-400/10 text-red-200">
                DSB
              </div>
            </div>
            <SequenceBlock label="Right arm" sequence={after} />
          </div>
          <div className="mt-5 rounded-lg border border-cyan-400/15 bg-cyan-400/5 p-4">
            <p className="mb-2 text-sm font-semibold text-cyan-100">{repairResult.label}</p>
            <p className="break-all font-mono text-sm leading-7 text-zinc-200">{repairResult.sequence}</p>
          </div>
        </div>
      </div>
    </section>
  );
}

interface SequenceBlockProps {
  label: string;
  sequence: string;
}

function SequenceBlock({ label, sequence }: SequenceBlockProps) {
  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-3">
      <p className="mb-2 text-xs uppercase tracking-[0.14em] text-zinc-500">{label}</p>
      <div className="grid grid-cols-4 gap-1">
        {sequence.split('').map((base, index) => (
          <span key={`${base}-${index}`} className="rounded border border-zinc-700 bg-zinc-950 px-2 py-2 text-center font-mono text-sm text-cyan-100">
            {base}
          </span>
        ))}
      </div>
    </div>
  );
}

interface AnalyticsProps {
  metrics: MetricCard[];
  logs: string[];
}

function AnalyticsDashboard({ metrics, logs }: AnalyticsProps) {
  return (
    <section className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-5 backdrop-blur-md">
      <SectionHeader icon={BarChart3} eyebrow="Feature 04" title="Synthetic Biology Analytics" />
      <div className="mt-5 grid gap-3 sm:grid-cols-2">
        {metrics.map((metric) => {
          const Icon = metric.icon;
          return (
            <div key={metric.label} className="rounded-lg border border-zinc-800 bg-zinc-950/70 p-4">
              <div className="flex items-start justify-between gap-3">
                <p className="text-sm text-zinc-400">{metric.label}</p>
                <Icon className={`h-5 w-5 ${metric.accent}`} />
              </div>
              <p className="mt-3 text-2xl font-semibold text-white">{metric.value}</p>
              <p className="mt-1 text-sm text-emerald-300">{metric.delta}</p>
            </div>
          );
        })}
      </div>
      <div className="mt-4 overflow-hidden rounded-lg border border-zinc-800 bg-black/70">
        <div className="flex items-center gap-2 border-b border-zinc-800 px-4 py-3 text-sm text-zinc-300">
          <Terminal className="h-4 w-4 text-emerald-300" />
          Live system events
        </div>
        <div className="h-48 space-y-2 overflow-hidden p-4 font-mono text-xs leading-5">
          {logs.map((log, index) => (
            <p
              key={`${log}-${index}`}
              className={
                log.includes('WARN')
                  ? 'text-amber-300'
                  : log.includes('SUCCESS')
                    ? 'text-emerald-300'
                    : log.includes('MODEL')
                      ? 'text-cyan-300'
                      : 'text-zinc-400'
              }
            >
              {log}
            </p>
          ))}
        </div>
      </div>
    </section>
  );
}

interface SectionHeaderProps {
  icon: typeof Activity;
  eyebrow: string;
  title: string;
}

function SectionHeader({ icon: Icon, eyebrow, title }: SectionHeaderProps) {
  return (
    <div className="flex items-center gap-3">
      <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-cyan-400/20 bg-cyan-400/10 text-cyan-300">
        <Icon className="h-5 w-5" />
      </div>
      <div>
        <p className="text-xs uppercase tracking-[0.18em] text-cyan-200/70">{eyebrow}</p>
        <h2 className="text-xl font-semibold tracking-normal text-white">{title}</h2>
      </div>
    </div>
  );
}

export default App;
