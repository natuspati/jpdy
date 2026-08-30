import Card from '@/components/ui/Card';

interface Props {
  answeringPlayerName: string;
  expectedAnswer?: string;
  onJudge: (correct: boolean) => void;
}

const HostJudgePanel = ({ answeringPlayerName, expectedAnswer, onJudge }: Props) => (
  <Card className="space-y-4 border-amber-400/40 p-4">
    <div>
      <p className="text-xs font-bold uppercase tracking-[0.18em] text-amber-300">Host action</p>
      <p className="mt-1 text-lg font-semibold text-slate-100">
        Listen to {answeringPlayerName}'s spoken answer.
      </p>
    </div>
    {expectedAnswer ? (
      <div>
        <p className="text-xs uppercase tracking-wide text-slate-400">Answer key</p>
        <p className="text-balance text-slate-200">{expectedAnswer}</p>
      </div>
    ) : null}
    <div className="grid grid-cols-2 gap-2">
      <button
        type="button"
        className="rounded-xl bg-rose-600 px-3 py-7 text-xl font-black uppercase tracking-wide text-white transition-colors hover:bg-rose-500 focus:outline-none focus:ring-2 focus:ring-amber-400 focus:ring-offset-2 focus:ring-offset-slate-950"
        onClick={() => onJudge(false)}
      >
        Wrong
      </button>
      <button
        type="button"
        className="rounded-xl bg-emerald-500 px-3 py-7 text-xl font-black uppercase tracking-wide text-slate-950 transition-colors hover:bg-emerald-400 focus:outline-none focus:ring-2 focus:ring-amber-400 focus:ring-offset-2 focus:ring-offset-slate-950"
        onClick={() => onJudge(true)}
      >
        Correct
      </button>
    </div>
  </Card>
);

export default HostJudgePanel;
