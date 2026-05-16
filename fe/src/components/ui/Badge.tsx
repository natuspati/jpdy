import { type ReactNode } from 'react';

type Tone = 'neutral' | 'success' | 'danger' | 'warning' | 'info';

const toneClasses: Record<Tone, string> = {
  neutral: 'bg-slate-700 text-slate-100',
  success: 'bg-emerald-700 text-emerald-50',
  danger: 'bg-rose-700 text-rose-50',
  warning: 'bg-amber-600 text-amber-50',
  info: 'bg-sky-700 text-sky-50',
};

interface BadgeProps {
  tone?: Tone;
  children: ReactNode;
}

const Badge = ({ tone = 'neutral', children }: BadgeProps) => (
  <span
    className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${toneClasses[tone]}`}
  >
    {children}
  </span>
);

export default Badge;
