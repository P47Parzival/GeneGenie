import { Binary, BrainCircuit, DatabaseZap, FlaskConical, GitBranch, ShieldCheck } from 'lucide-react';
import SectionHeader from '../components/SectionHeader';

const capabilities = [
  {
    title: 'Foundation model design layer',
    description: 'Model adapters are structured around target context, editor constraints, PAM requirements, and review metadata.',
    icon: BrainCircuit,
  },
  {
    title: 'Sequence intelligence graph',
    description: 'Connect candidate sequences, annotations, assay plans, provenance, and review status without coupling the UI to mock data.',
    icon: GitBranch,
  },
  {
    title: 'Wet-lab feedback readiness',
    description: 'Portal primitives are prepared for assay ingestion, batch states, confidence envelopes, and validation summaries.',
    icon: FlaskConical,
  },
];

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

      <section className="grid gap-4 lg:grid-cols-3">
        {capabilities.map((capability) => {
          const Icon = capability.icon;
          return (
            <article key={capability.title} className="rounded-lg border border-zinc-800 bg-zinc-900/45 p-5 backdrop-blur-md">
              <Icon className="h-6 w-6 text-cyan-300" />
              <h2 className="mt-5 text-xl font-semibold text-white">{capability.title}</h2>
              <p className="mt-3 text-sm leading-6 text-zinc-300">{capability.description}</p>
            </article>
          );
        })}
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
