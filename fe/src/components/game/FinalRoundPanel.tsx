import { useState } from 'react';

import Button from '@/components/ui/Button';
import Field from '@/components/ui/Field';
import Input from '@/components/ui/Input';
import { useCountdown } from '@/hooks/useCountdown';
import { preloadedSrc } from '@/hooks/useBoardMediaPreload';
import type { GameLobbyState } from '@/schemas';
import { currentCategoryName, currentPrompt } from '@/services/game/gameDerivations';
import {
  canAdvanceFinalReveal,
  canJudgeFinalAnswer,
  canSubmitFinalAnswer,
  canSubmitFinalWager,
} from '@/services/game/phaseGuards';
import type { ClientEventName, ClientToServerEvents } from '@/sockets/types';
import JudgeButtons from './JudgeButtons';
import PromptMedia from './PromptMedia';
import PromptStage from './PromptStage';

interface Props {
  state: GameLobbyState;
  userId: number;
  connected: boolean;
  pendingCommand?: ClientEventName | null;
  commandError?: string | null;
  emit: <E extends ClientEventName>(
    event: E,
    ...args: Parameters<ClientToServerEvents[E]>
  ) => boolean;
}

const verdictClass = (correct: boolean | null): string =>
  correct === null
    ? 'border-slate-700 bg-slate-900/80'
    : correct
      ? 'animate-verdict-correct border-emerald-400/70 bg-emerald-400/10 motion-reduce:animate-none'
      : 'animate-verdict-wrong border-rose-400/70 bg-rose-400/10 motion-reduce:animate-none';

const FinalRoundPanel = ({
  state,
  userId,
  connected,
  pendingCommand,
  commandError,
  emit,
}: Props) => {
  const [wager, setWager] = useState('0');
  const [answer, setAnswer] = useState('');
  const seconds = useCountdown(state.timer_deadline);
  const final = state.final_round;
  if (!final) return null;
  const own = final.players.find((player) => player.user_id === userId);
  const current = final.players.find((player) => player.user_id === final.current_user_id);
  const prompt = currentPrompt(state);
  const isHost = state.host.user_id === userId;
  const blocked = !connected || !!pendingCommand;
  const canWager = canSubmitFinalWager(state, userId) && seconds !== 0;
  const canAnswer = canSubmitFinalAnswer(state, userId) && seconds !== 0;
  const amount = Number(wager);
  const validWager =
    wager.trim() !== '' && Number.isInteger(amount) && amount >= 0 && amount <= final.max_wager;
  const submitted = own?.decision_submitted && !own.removed;

  return (
    <section aria-label="Final round" className="flex min-h-0 flex-1 flex-col gap-3">
      <h2 className="text-center text-xl font-bold text-amber-300">
        Final · {currentCategoryName(state)}
      </h2>
      {commandError ? (
        <p role="alert" className="text-rose-300">
          {commandError}
        </p>
      ) : null}
      {pendingCommand ? <p role="status">Sending…</p> : null}
      {state.phase !== 'final_betting' && submitted ? (
        <p className="text-center text-sm text-slate-300">
          {own.wager === null ? 'Sitting out.' : `Your wager: ${own.wager}`}
        </p>
      ) : null}
      {state.phase === 'final_betting' && canWager ? (
        <form
          onSubmit={(event) => {
            event.preventDefault();
            if (!blocked && validWager && canSubmitFinalWager(state, userId)) {
              emit('submit_final_wager', { amount });
            }
          }}
          className="mx-auto flex w-full max-w-md items-end gap-2"
        >
          <div className="flex-1">
            <Field label="Your Final wager" htmlFor="final-wager" hint={`0 to ${final.max_wager}`}>
              <Input
                id="final-wager"
                type="number"
                min={0}
                max={final.max_wager}
                step={1}
                value={wager}
                disabled={blocked}
                onChange={(event) => setWager(event.target.value)}
              />
            </Field>
          </div>
          <Button type="submit" disabled={blocked || !validWager}>
            Bet
          </Button>
        </form>
      ) : null}
      {state.phase === 'final_betting' && !canWager && submitted ? (
        <p role="status" className="text-center text-2xl font-bold text-slate-100">
          ✓ {own.wager ?? 0}
        </p>
      ) : null}
      {state.phase === 'final_answering' && prompt ? (
        <PromptStage prompt={prompt} categoryName={currentCategoryName(state)} />
      ) : null}
      {state.phase === 'final_answering' ? (
        <div className="mx-auto w-full max-w-xl space-y-2">
          {canAnswer ? (
            <form
              className="flex items-end gap-2"
              onSubmit={(event) => {
                event.preventDefault();
                if (!blocked && canSubmitFinalAnswer(state, userId)) {
                  emit('submit_final_answer', { answer });
                }
              }}
            >
              <div className="flex-1">
                <Field label="Your Final answer" htmlFor="final-answer">
                  <Input
                    id="final-answer"
                    value={answer}
                    maxLength={256}
                    disabled={blocked}
                    autoComplete="off"
                    onChange={(event) => setAnswer(event.target.value)}
                  />
                </Field>
              </div>
              <Button type="submit" disabled={blocked}>
                Submit
              </Button>
            </form>
          ) : own?.answer_submitted && !own.removed ? (
            <p role="status" className="text-center">
              ✓ {own.answer?.trim() || 'Not submitted'}
            </p>
          ) : null}
        </div>
      ) : null}
      {state.phase === 'final_reveal' ? (
        <>
          <div
            data-testid="final-showdown"
            className={`flex min-h-0 flex-1 flex-col items-center justify-between gap-4 overflow-y-auto rounded-xl border p-4 text-center sm:p-6 ${verdictClass(current?.correct ?? null)}`}
          >
            <section aria-label="Correct Final answer" className="w-full">
              <p className="text-balance text-4xl font-black text-amber-300 sm:text-6xl">
                {final.correct_answer}
              </p>
            </section>
            {final.correct_answer_media && final.correct_answer_type ? (
              <div className="flex min-h-0 w-full flex-1 items-center justify-center">
                <PromptMedia
                  contentType={final.correct_answer_type}
                  media={final.correct_answer_media}
                  src={preloadedSrc(final.correct_answer_media)}
                  alt={`Correct answer: ${final.correct_answer ?? ''}`}
                  playbackId={`final:${state.current_prompt_id}:answer`}
                />
              </div>
            ) : (
              <div className="flex-1" />
            )}
            {current?.revealed ? (
              <p
                aria-label="Current Final response"
                className="w-full text-balance text-3xl font-black text-slate-50 sm:text-5xl"
              >
                {current.username} ({current.wager ?? 0}):{' '}
                {current.answer?.trim() || 'Not submitted'}
              </p>
            ) : null}
          </div>
          {isHost && current ? (
            <div className="mx-auto w-full max-w-xs sm:max-w-md">
              <JudgeButtons
                canJudge={!blocked && canJudgeFinalAnswer(state, userId)}
                canAdvance={!blocked && canAdvanceFinalReveal(state, userId)}
                onJudge={(correct) =>
                  emit('judge_final_answer', { user_id: current.user_id, correct })
                }
                onNext={() => emit('advance_final_reveal', { user_id: current.user_id })}
                nextLabel={final.is_last_reveal ? 'Finish' : 'Next'}
              />
            </div>
          ) : null}
        </>
      ) : null}
    </section>
  );
};

export default FinalRoundPanel;
