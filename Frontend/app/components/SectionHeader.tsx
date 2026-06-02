import type { LucideIcon } from 'lucide-react';

interface SectionHeaderProps {
  icon: LucideIcon;
  eyebrow: string;
  title: string;
  description?: string;
}

export default function SectionHeader({ icon: Icon, eyebrow, title, description }: SectionHeaderProps) {
  return (
    <div className="flex items-start gap-3">
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-cyan-400/20 bg-cyan-400/10 text-cyan-300">
        <Icon className="h-5 w-5" />
      </div>
      <div>
        <p className="text-xs uppercase tracking-[0.18em] text-cyan-200/70">{eyebrow}</p>
        <h2 className="mt-1 text-2xl font-semibold tracking-normal text-white">{title}</h2>
        {description ? <p className="mt-2 max-w-3xl text-sm leading-6 text-zinc-300">{description}</p> : null}
      </div>
    </div>
  );
}
