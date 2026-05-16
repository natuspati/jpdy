import Button from '@/components/ui/Button';
import Card from '@/components/ui/Card';

interface Props {
  submittedAnswer: string | null;
  expectedAnswer?: string;
  onJudge: (correct: boolean) => void;
}

const HostJudgePanel = ({ submittedAnswer, expectedAnswer, onJudge }: Props) => (
  <Card className="space-y-3">
    <div>
      <p className="text-xs uppercase tracking-wide text-slate-400">Player said</p>
      <p className="text-balance text-lg font-semibold text-slate-100">
        {submittedAnswer || '(no answer)'}
      </p>
    </div>
    {expectedAnswer ? (
      <div>
        <p className="text-xs uppercase tracking-wide text-slate-400">Expected</p>
        <p className="text-balance text-slate-200">{expectedAnswer}</p>
      </div>
    ) : null}
    <div className="grid grid-cols-2 gap-2">
      <Button variant="danger" size="lg" onClick={() => onJudge(false)}>
        Wrong
      </Button>
      <Button size="lg" onClick={() => onJudge(true)}>
        Correct
      </Button>
    </div>
  </Card>
);

export default HostJudgePanel;
