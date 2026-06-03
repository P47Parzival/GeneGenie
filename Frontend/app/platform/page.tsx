import { Binary, BrainCircuit, DatabaseZap, FlaskConical, GitBranch, ShieldCheck, Target } from 'lucide-react';
import SectionHeader from '../components/SectionHeader';

const inputs = [
  { label: 'Raw Data', icon: DatabaseZap },
  { label: 'Logical Rules', icon: Binary },
  { label: 'Knowledge Base', icon: BrainCircuit },
  { label: 'Agent Roles', icon: Target },
];

const layers = ['Structured Knowledge Graph', 'Optimized Workflow', 'Actionable Insights', 'Agentic Loop'];

const leftPills = ['Raw Data Ingestion', 'Task Orchestration', 'Real-time Analytics', 'Autonomous Actions'];
const rightPills = ['Semantic Linking', 'Agent Collaboration', 'Predictive Models', 'API Integrations'];

export default function PlatformPage() {
  return (
    <main className="flex flex-col gap-10 pb-16">
      <section className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-8 shadow-bio backdrop-blur-md">
        <p className="text-xs uppercase tracking-[0.18em] text-cyan-200/70">Platform</p>
        <h1 className="mt-4 max-w-4xl text-5xl font-semibold tracking-normal text-white">
          AI-native gene editor design with governed scientific workflows.
        </h1>
        <p className="mt-5 max-w-3xl text-lg leading-8 text-zinc-300">
          GeneGenie separates product surfaces from data contracts so model services, internal APIs, and experimental evidence can be connected without rewriting the application.
        </p>
      </section>

      <section className="rounded-lg border border-zinc-800 bg-zinc-950/60 p-6 backdrop-blur-md">
        <div className="flex flex-col gap-6">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {inputs.map((input) => {
              const Icon = input.icon;
              return (
                <div key={input.label} className="platform-input-card">
                  <Icon className="h-5 w-5 text-cyan-200" />
                  <span className="text-sm text-zinc-100">{input.label}</span>
                  <div className="platform-input-arrow" aria-hidden="true" />
                </div>
              );
            })}
          </div>

          <div className="platform-funnel">
            <svg viewBox="0 0 240 120" aria-hidden="true" className="platform-funnel-svg">
              <defs>
                <linearGradient id="funnelGlow" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor="rgba(34, 211, 238, 0.6)" />
                  <stop offset="50%" stopColor="rgba(16, 185, 129, 0.6)" />
                  <stop offset="100%" stopColor="rgba(34, 211, 238, 0.6)" />
                </linearGradient>
              </defs>
              <ellipse cx="120" cy="44" rx="85" ry="24" className="platform-funnel-ring platform-funnel-ring-1" />
              <ellipse cx="120" cy="76" rx="55" ry="16" className="platform-funnel-ring platform-funnel-ring-2" />
              <ellipse cx="120" cy="96" rx="30" ry="10" className="platform-funnel-ring platform-funnel-ring-3" />
              <line x1="120" y1="24" x2="120" y2="108" className="platform-funnel-axis" />
              <line x1="120" y1="24" x2="120" y2="108" className="platform-funnel-axis platform-funnel-axis-flow" />
            </svg>
          </div>

          <div className="platform-down-arrows" aria-hidden="true">
            {Array.from({ length: 4 }).map((_, index) => (
              <span key={index} className="platform-down-arrow" />
            ))}
          </div>

          <div className="platform-stack-grid">
            {layers.map((layer, index) => (
              <div key={layer} className="platform-stack-row">
                <span className="platform-pill">{leftPills[index]}</span>
                <span
                  className="platform-flow-line platform-flow-line-left"
                  style={{ '--flow-delay': `${index * 0.35}s` } as React.CSSProperties}
                  aria-hidden="true"
                />
                <div className="platform-layer">
                  <span>{layer}</span>
                </div>
                <span
                  className="platform-flow-line platform-flow-line-right"
                  style={{ '--flow-delay': `${index * 0.35 + 0.2}s` } as React.CSSProperties}
                  aria-hidden="true"
                />
                <span className="platform-pill">{rightPills[index]}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="rounded-lg border border-zinc-800 bg-zinc-900/45 p-6 backdrop-blur-md">
        <SectionHeader
          icon={DatabaseZap}
          eyebrow="Technical overview"
          title="Designed around replaceable data contracts"
          description="The portal uses explicit interfaces for metrics, event logs, and sequence grid cells. Empty and loading states are first-class so integration can begin before backend availability."
        />
        <div className="mt-8 grid gap-4 md:grid-cols-3">
          {[
            ['DashboardMetrics', 'Operational metrics loaded from an API boundary.'],
            ['SystemEvent', 'Timestamped workflow events from orchestration services.'],
            ['SequenceGridCell', 'Visualizer cells representing indexed biological regions.'],
          ].map(([name, copy]) => (
            <div key={name} className="rounded-lg border border-zinc-800 bg-zinc-950/70 p-4">
              <Binary className="h-5 w-5 text-emerald-300" />
              <p className="mt-4 font-mono text-sm text-cyan-100">{name}</p>
              <p className="mt-2 text-sm leading-6 text-zinc-400">{copy}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="rounded-lg border border-emerald-400/20 bg-emerald-400/10 p-6">
        <div className="flex items-start gap-3">
          <ShieldCheck className="mt-1 h-6 w-6 shrink-0 text-emerald-300" />
          <div>
            <h2 className="text-xl font-semibold text-emerald-50">Production posture</h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-emerald-100/80">
              Authentication, API clients, and persistence are intentionally isolated from the marketing pages. The portal page is ready for integration with session-aware server routes or client-side data libraries.
            </p>
          </div>
        </div>
      </section>
    </main>
  );
}

