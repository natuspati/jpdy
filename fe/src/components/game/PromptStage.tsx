import type { GamePromptState } from '@/schemas';

interface Props {
  prompt: GamePromptState;
}

const PromptStage = ({ prompt }: Props) => (
  <div className="flex flex-col items-center gap-4 rounded-md border border-slate-800 bg-slate-900/70 p-4">
    <div className="text-xs uppercase tracking-wide text-amber-300">{prompt.score_value} pts</div>
    <p className="text-balance text-center text-[clamp(1.25rem,4vw,2.5rem)]">
      {prompt.question}
    </p>
  </div>
);

export default PromptStage;
