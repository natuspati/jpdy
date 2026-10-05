import Card from '@/components/ui/Card';

interface Props {
  answeringPlayerName: string;
  expectedAnswer?: string;
}

const HostJudgePanel = ({ answeringPlayerName, expectedAnswer }: Props) => (
  <Card className="mx-auto w-full max-w-xs space-y-2 border-amber-400/40 p-3 text-center sm:max-w-md">
    <div>
      <p className="text-xs font-bold uppercase tracking-[0.18em] text-amber-300">Answering</p>
      <p className="text-sm font-semibold text-slate-100">
        Listen to {answeringPlayerName}'s spoken answer.
      </p>
    </div>
    {expectedAnswer ? (
      <div>
        <p className="text-xs uppercase tracking-wide text-slate-400">Answer key</p>
        <p className="text-balance text-slate-200">{expectedAnswer}</p>
      </div>
    ) : null}
  </Card>
);

export default HostJudgePanel;
