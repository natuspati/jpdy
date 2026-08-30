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
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs text-slate-400">
        <span>Time</span>
        <span className="tabular-nums">{remaining}s</span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-slate-800">
        <div
          className={`h-full transition-[width] duration-200 ease-linear ${tone}`}
          style={{ width: `${pct}%` }}
          aria-label={`Time remaining ${remaining} seconds`}
        />
      </div>
    </div>
  );
};

export default TimerBar;
