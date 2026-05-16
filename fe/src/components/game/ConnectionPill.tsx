import type { PlayerConnectionStatusEnum } from '@/schemas';

const ConnectionPill = ({ status }: { status: PlayerConnectionStatusEnum }) => {
  const dotClass = status === 'connected' ? 'bg-emerald-400' : 'bg-slate-500';
  return (
    <span
      title={status}
      aria-label={status}
      className={`inline-block h-2 w-2 rounded-full ${dotClass}`}
    />
  );
};

export default ConnectionPill;
