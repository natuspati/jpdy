import Card from '@/components/ui/Card';

interface Props {
  expectedAnswer?: string;
}

const HostJudgePanel = ({ expectedAnswer }: Props) => (
  <Card className="mx-auto w-full max-w-xs space-y-2 border-amber-400/40 p-3 text-center sm:max-w-md">
    {expectedAnswer ? <p className="text-balance text-slate-200">{expectedAnswer}</p> : null}
  </Card>
);

export default HostJudgePanel;
