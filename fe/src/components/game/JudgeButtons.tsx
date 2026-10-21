interface Props {
  canJudge: boolean;
  canAdvance: boolean;
  onJudge: (correct: boolean) => void;
  onNext: () => void;
  nextLabel?: string;
}

const base =
  'rounded-md px-2 py-2.5 text-sm font-bold transition-colors focus:outline-none focus:ring-2 focus:ring-amber-400 focus:ring-offset-2 focus:ring-offset-slate-950 disabled:bg-slate-800 disabled:text-slate-500';

const JudgeButtons = ({ canJudge, canAdvance, onJudge, onNext, nextLabel = 'Next' }: Props) => (
  <div className="grid grid-cols-3 gap-1.5 sm:gap-2">
    <button
      type="button"
      disabled={!canJudge}
      onClick={() => onJudge(true)}
      className={`${base} bg-emerald-500 text-slate-950 hover:bg-emerald-400`}
    >
      Accept
    </button>
    <button
      type="button"
      disabled={!canJudge}
      onClick={() => onJudge(false)}
      className={`${base} bg-rose-600 text-white hover:bg-rose-500`}
    >
      Decline
    </button>
    <button
      type="button"
      disabled={!canAdvance}
      onClick={onNext}
      className={`${base} bg-amber-400 text-slate-950 hover:bg-amber-300`}
    >
      {nextLabel}
    </button>
  </div>
);

export default JudgeButtons;
