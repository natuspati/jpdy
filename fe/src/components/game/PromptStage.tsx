import type {
  GamePromptState,
  GameResolutionEnum,
  MediaReference,
  PromptContentType,
} from '@/schemas';
import PromptMedia from './PromptMedia';

interface Props {
  prompt: GamePromptState;
  answer?: string | null;
  answerType?: PromptContentType | null;
  answerMedia?: MediaReference | null;
  resolution?: GameResolutionEnum | null;
}

const PromptStage = ({
  prompt,
  answer = null,
  answerType = null,
  answerMedia = null,
  resolution = null,
}: Props) => {
  const isReveal = answer !== null;
  const text = isReveal ? answer : prompt.question;
  const contentType = isReveal ? (answerType ?? 'text') : (prompt.question_type ?? 'text');
  const media = isReveal ? answerMedia : prompt.question_media;
  const hasMedia = contentType !== 'text' && media !== null && media !== undefined;
  const resolutionTone =
    resolution === 'correct'
      ? 'border-emerald-400/70 bg-emerald-400/10 text-emerald-50'
      : resolution === 'unanswered' || resolution === 'expired'
        ? 'border-rose-400/70 bg-rose-400/10 text-rose-50'
        : 'border-slate-700 bg-slate-900/80 text-slate-50';
  const scoreTone =
    resolution === 'correct'
      ? 'text-emerald-200'
      : resolution === 'unanswered' || resolution === 'expired'
        ? 'text-rose-200'
        : 'text-amber-300';

  return (
    <section
      aria-label="Prompt stage"
      data-resolution={resolution ?? undefined}
      className={`relative flex min-h-[20rem] overflow-hidden rounded-xl border p-6 shadow-2xl shadow-slate-950/30 sm:min-h-[28rem] sm:p-10 ${resolutionTone}`}
    >
      <div
        aria-label={`${prompt.score_value} points`}
        className={`absolute right-4 top-4 text-xs font-bold uppercase tracking-[0.2em] sm:right-6 sm:top-6 ${scoreTone}`}
      >
        {prompt.score_value}
      </div>
      <div
        data-testid="prompt-stage-content"
        className={`flex min-h-0 w-full flex-1 flex-col items-center gap-5 ${
          hasMedia ? 'justify-start pt-8' : 'justify-center'
        }`}
      >
        <p
          className={`text-balance text-center font-semibold leading-tight ${
            hasMedia
              ? 'max-w-4xl text-[clamp(1.25rem,3vw,2.25rem)]'
              : 'max-w-5xl text-[clamp(1.5rem,4.5vw,3.25rem)]'
          }`}
        >
          {text}
        </p>
        {hasMedia ? (
          <div className="flex min-h-0 w-full flex-1 items-center justify-center">
            <PromptMedia
              contentType={contentType}
              media={media}
              alt={isReveal ? `Answer: ${text}` : text}
              playbackId={`${prompt.prompt_id}:${isReveal ? 'answer' : 'question'}`}
            />
          </div>
        ) : null}
      </div>
    </section>
  );
};

export default PromptStage;
