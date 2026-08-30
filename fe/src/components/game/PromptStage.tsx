import type { GamePromptState, GameResolutionEnum } from '@/schemas';
import PromptMedia from './PromptMedia';

interface Props {
  prompt: GamePromptState;
  answer?: string | null;
  answerType?: import('@/schemas').PromptContentType | null;
  answerMedia?: import('@/schemas').MediaReference | null;
  resolution?: GameResolutionEnum | null;
}

const resolutionMessage: Record<GameResolutionEnum, string> = {
  correct: 'Correct response.',
  unanswered: 'No correct response.',
  expired: 'Time expired.',
};

const PromptStage = ({
  prompt,
  answer = null,
  answerType = null,
  answerMedia = null,
  resolution = null,
}: Props) => (
  <section
    aria-label="Prompt stage"
    className="flex min-h-[20rem] flex-col items-center justify-center gap-5 rounded-xl border border-slate-700 bg-slate-900/80 p-6 shadow-2xl shadow-slate-950/30 sm:min-h-[28rem] sm:p-10"
  >
    <div className="text-xs font-bold uppercase tracking-[0.2em] text-amber-300">
      {prompt.score_value} points
    </div>
    <p className="text-balance text-center text-[clamp(1.5rem,4.5vw,3.25rem)] font-semibold leading-tight text-slate-50">
      {prompt.question}
    </p>
    <PromptMedia
      contentType={prompt.question_type ?? 'text'}
      media={prompt.question_media}
      alt={prompt.question}
    />
    {answer !== null ? (
      <div className="w-full max-w-2xl space-y-2 rounded-lg border border-emerald-400/30 bg-emerald-400/10 p-4 text-center">
        {resolution ? (
          <p className="text-sm font-semibold uppercase tracking-wide text-emerald-200">
            {resolutionMessage[resolution]}
          </p>
        ) : null}
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-slate-400">
          Correct answer
        </p>
        <p className="text-balance text-xl font-semibold text-white sm:text-2xl">{answer}</p>
        {answerMedia && answerType ? (
          <PromptMedia contentType={answerType} media={answerMedia} alt={`Answer: ${answer}`} />
        ) : null}
      </div>
    ) : null}
  </section>
);

export default PromptStage;
