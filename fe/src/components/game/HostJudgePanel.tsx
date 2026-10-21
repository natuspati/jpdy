import Card from '@/components/ui/Card';

interface Props {
  answeringPlayerName: string;
  expectedAnswer?: string;
}

const HostJudgePanel = ({ answeringPlayerName, expectedAnswer }: Props) => (
  <Card className="mx-auto w-full max-w-xs space-y-2 border-amber-400/40 p-3 text-center sm:max-w-md">
    <p className="text-sm font-semibold text-amber-300">{answeringPlayerName}</p>
    {expectedAnswer ? <p className="text-balance text-slate-200">{expectedAnswer}</p> : null}
  </Card>
);

export default HostJudgePanel;
