import { Leaf, Microscope, Sprout, TestTube2 } from 'lucide-react';
import Image from 'next/image';

const applications = [
  {
    title: 'Antibodies',
    description: 'Editor and guide design workflows for translational programs that require precision, reviewability, and evidence capture.',
    icon: TestTube2,
    image: '/antibodies.jpg',
    imageAlt: 'Antibody structure visualization',
  },
  {
    title: 'Agriculture',
    description: 'Sequence design infrastructure for crop resilience, trait exploration, and scalable research collaboration.',
    icon: Sprout,
    image: '/agriculture.png',
    imageAlt: 'Agricultural biotechnology visualization',
  },
  {
    title: 'Research',
    description: 'A governed workspace for academic and industry teams exploring sequence-function relationships.',
    icon: Microscope,
    image: '/research.png',
    imageAlt: 'Research laboratory visualization',
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
              <div className="relative mt-6 h-44 overflow-hidden rounded-lg border border-zinc-800 bg-black">
                <Image
                  src={application.image}
                  alt={application.imageAlt}
                  fill
                  sizes="(min-width: 1024px) 33vw, 100vw"
                  className="object-cover brightness-90 contrast-125 saturate-125 transition duration-500 hover:scale-[1.03]"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-zinc-950 via-zinc-950/20 to-transparent" />
                <div className="absolute inset-0 ring-1 ring-inset ring-white/5" />
                <div className="absolute bottom-3 left-3 rounded-md border border-cyan-400/20 bg-zinc-950/70 px-3 py-1.5 text-xs text-cyan-100 backdrop-blur-md">
                  {application.title} workspace
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
