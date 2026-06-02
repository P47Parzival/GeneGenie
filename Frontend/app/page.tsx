import { ArrowRight, Building2, Dna, FlaskConical, Microscope, ShieldCheck, Sparkles } from 'lucide-react';
import Link from 'next/link';
import SectionHeader from './components/SectionHeader';

const pillars = [
  {
    title: 'Author editor candidates',
    description: 'Transform target specifications into ranked editor, guide, and delivery design candidates.',
    icon: Dna,
  },
  {
    title: 'Validate across constraints',
    description: 'Coordinate model evidence, assay readiness, and sequence risk review before work moves downstream.',
    icon: ShieldCheck,
  },
  {
    title: 'Operationalize biology teams',
    description: 'Give discovery, translational, and platform teams one governed interface for design programs.',
    icon: Building2,
  },
];

export default function HomePage() {
  return (
    <main className="flex flex-col gap-16 pb-16">
      <section className="overflow-hidden rounded-lg border border-zinc-800 bg-zinc-900/50 p-6 shadow-bio backdrop-blur-md sm:p-8 lg:p-10">
        <div className="grid gap-8 lg:grid-cols-[1.05fr_0.95fr] lg:items-center">
          <div>
            <div className="mb-5 inline-flex items-center gap-2 rounded-md border border-cyan-400/25 bg-cyan-400/10 px-3 py-1 text-sm text-cyan-200">
              <Sparkles className="h-4 w-4" />
              Enterprise AI for programmable biology
            </div>
            <h1 className="max-w-4xl text-5xl font-semibold tracking-normal text-white sm:text-6xl">
              Gene editing infrastructure for teams designing the next biology stack.
            </h1>
            <p className="mt-5 max-w-2xl text-lg leading-8 text-zinc-300">
              GeneGenie unifies sequence intelligence, editor design workflows, and governed AI review into a production-ready
              environment for modern life-science organizations.
            </p>
            <div className="mt-7 flex flex-wrap gap-3">
              <Link href="/platform" className="inline-flex items-center gap-2 rounded-md bg-cyan-300 px-5 py-3 font-semibold text-zinc-950 transition hover:bg-cyan-200">
                Explore platform
                <ArrowRight className="h-4 w-4" />
              </Link>
              <Link href="/portal" className="inline-flex items-center gap-2 rounded-md border border-zinc-700 px-5 py-3 font-semibold text-zinc-100 transition hover:border-cyan-400/60 hover:text-cyan-100">
                Access portal
              </Link>
            </div>
          </div>
          <div className="rounded-lg border border-zinc-800 bg-zinc-950/70 p-4">
            <div className="grid grid-cols-12 gap-1">
              {Array.from({ length: 108 }).map((_, index) => (
                <div
                  key={index}
                  className={`h-8 rounded-sm border ${
                    index % 17 === 0
                      ? 'border-cyan-300/40 bg-cyan-400/25'
                      : index % 11 === 0
                        ? 'border-emerald-300/30 bg-emerald-400/20'
                        : 'border-zinc-800 bg-zinc-900/80'
                  }`}
                />
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        {pillars.map((pillar) => {
          const Icon = pillar.icon;
          return (
            <article key={pillar.title} className="rounded-lg border border-zinc-800 bg-zinc-900/45 p-5 backdrop-blur-md">
              <Icon className="h-6 w-6 text-cyan-300" />
              <h2 className="mt-5 text-xl font-semibold text-white">{pillar.title}</h2>
              <p className="mt-3 text-sm leading-6 text-zinc-300">{pillar.description}</p>
            </article>
          );
        })}
      </section>

      <section className="rounded-lg border border-zinc-800 bg-zinc-900/45 p-6 backdrop-blur-md">
        <SectionHeader
          icon={Microscope}
          eyebrow="Built for translation"
          title="From design intent to biological evidence"
          description="A corporate-grade workflow surface for partners who need model outputs to become auditable scientific programs."
        />
        <div className="mt-8 grid gap-4 md:grid-cols-3">
          {['Sequence design', 'Editor optimization', 'Assay planning'].map((item) => (
            <div key={item} className="rounded-lg border border-zinc-800 bg-zinc-950/60 p-4">
              <FlaskConical className="h-5 w-5 text-emerald-300" />
              <p className="mt-4 font-semibold text-zinc-100">{item}</p>
              <p className="mt-2 text-sm leading-6 text-zinc-400">
                Structured modules designed for real backend data, permissioning, and validation evidence.
              </p>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}
