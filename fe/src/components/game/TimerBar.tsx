import { useCountdown } from '@/hooks/useCountdown';

interface Props {
  deadline: string | null;
  totalSeconds?: number;
}

const TimerBar = ({ deadline, totalSeconds = 30 }: Props) => {
  const remaining = useCountdown(deadline);
  if (remaining === null) return null;
  const pct = Math.max(0, Math.min(100, (remaining / totalSeconds) * 100));
  const tone = remaining <= 3 ? 'bg-rose-500' : remaining <= 10 ? 'bg-amber-400' : 'bg-emerald-400';
  return (
    <div className="flex items-center gap-2 text-xs text-slate-400">
      <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-800">
        <div
          className={`h-full transition-[width] duration-200 ease-linear ${tone}`}
          style={{ width: `${pct}%` }}
          aria-label={`Time remaining ${remaining} seconds`}
        />
      </div>
      <span className="w-8 text-right tabular-nums">{remaining}s</span>
    </div>
  );
};

export default TimerBar;
