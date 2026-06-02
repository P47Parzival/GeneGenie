import { Leaf, Microscope, Sprout, TestTube2 } from 'lucide-react';

const applications = [
  {
    title: 'Therapeutics',
    description: 'Editor and guide design workflows for translational programs that require precision, reviewability, and evidence capture.',
    icon: TestTube2,
  },
  {
    title: 'Agriculture',
    description: 'Sequence design infrastructure for crop resilience, trait exploration, and scalable research collaboration.',
    icon: Sprout,
  },
  {
    title: 'Research',
    description: 'A governed workspace for academic and industry teams exploring sequence-function relationships.',
    icon: Microscope,
  },
];

export default function ApplicationsPage() {
  return (
    <main className="flex flex-col gap-10 pb-16">
      <section className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-8 shadow-bio backdrop-blur-md">
        <p className="text-xs uppercase tracking-[0.18em] text-cyan-200/70">Applications</p>
        <h1 className="mt-4 max-w-4xl text-5xl font-semibold tracking-normal text-white">
          Gene editing workflows for high-stakes biological programs.
        </h1>
        <p className="mt-5 max-w-3xl text-lg leading-8 text-zinc-300">
          GeneGenie is structured for teams that need a single interface across discovery, validation, and operational review.
        </p>
      </section>

      <section className="grid gap-4 lg:grid-cols-3">
        {applications.map((application) => {
          const Icon = application.icon;
          return (
            <article key={application.title} className="rounded-lg border border-zinc-800 bg-zinc-900/45 p-6 backdrop-blur-md">
              <Icon className="h-7 w-7 text-cyan-300" />
              <h2 className="mt-6 text-2xl font-semibold text-white">{application.title}</h2>
              <p className="mt-4 text-sm leading-6 text-zinc-300">{application.description}</p>
              <div className="mt-6 h-32 rounded-lg border border-zinc-800 bg-zinc-950/70 p-3">
                <div className="grid h-full grid-cols-8 gap-1">
                  {Array.from({ length: 32 }).map((_, index) => (
                    <span
                      key={index}
                      className={`rounded-sm border ${
                        index % 9 === 0 ? 'border-emerald-300/30 bg-emerald-400/20' : 'border-zinc-800 bg-zinc-900'
                      }`}
                    />
                  ))}
                </div>
              </div>
            </article>
          );
        })}
      </section>

      <section className="rounded-lg border border-cyan-400/20 bg-cyan-400/10 p-6">
        <div className="flex items-start gap-3">
          <Leaf className="mt-1 h-6 w-6 shrink-0 text-cyan-200" />
          <div>
            <h2 className="text-xl font-semibold text-cyan-50">Partner-ready by design</h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-cyan-100/80">
              Each application area can map to authenticated workspaces, project-level permissions, and API-driven program status without changing the public marketing pages.
            </p>
          </div>
        </div>
      </section>
    </main>
  );
}
