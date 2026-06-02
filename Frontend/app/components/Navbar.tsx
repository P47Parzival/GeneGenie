'use client';

import { Dna, Radio } from 'lucide-react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

const links = [
  { label: 'Home', href: '/' },
  { label: 'Platform', href: '/platform' },
  { label: 'Applications', href: '/applications' },
];

export default function Navbar() {
  const pathname = usePathname();

  return (
    <nav className="sticky top-3 z-20 mb-6 flex flex-col gap-3 rounded-lg border border-zinc-800 bg-zinc-950/82 px-4 py-3 shadow-bio backdrop-blur-md lg:flex-row lg:items-center lg:justify-between">
      <Link href="/" className="flex items-center gap-3">
        <div className="flex h-11 w-11 items-center justify-center rounded-lg border border-cyan-400/30 bg-cyan-400/10 text-cyan-300">
          <Dna className="h-6 w-6" />
        </div>
        <div>
          <p className="text-lg font-semibold tracking-normal text-white">GeneGenie</p>
          <p className="text-xs uppercase tracking-[0.18em] text-cyan-200/70">AI gene-editing infrastructure</p>
        </div>
      </Link>

      <div className="flex flex-wrap items-center gap-2 text-sm text-zinc-300">
        {links.map((link) => {
          const isActive = pathname === link.href;
          return (
            <Link
              key={link.href}
              href={link.href}
              className={`rounded-md px-3 py-2 transition ${
                isActive ? 'bg-zinc-800 text-cyan-200' : 'hover:bg-zinc-800 hover:text-cyan-200'
              }`}
            >
              {link.label}
            </Link>
          );
        })}
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2 rounded-md border border-emerald-400/20 bg-emerald-400/10 px-3 py-2 text-sm text-emerald-200">
          <Radio className="h-4 w-4 text-cyan-300" />
          Backend ready
        </div>
        <Link
          href="/portal"
          className="inline-flex items-center justify-center rounded-md bg-cyan-300 px-4 py-2 text-sm font-semibold text-zinc-950 transition hover:bg-cyan-200"
        >
          Access Portal
        </Link>
      </div>
    </nav>
  );
}
