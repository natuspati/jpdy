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

const FinalRoundPanel = ({
  state,
  userId,
  connected,
  pendingCommand,
  commandError,
  emit,
}: Props) => {
  const [wager, setWager] = useState('');
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
    wager.trim() !== '' &&
    Number.isInteger(amount) &&
    amount >= 1 &&
    amount <= (own?.score_before_final ?? 0);

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
      {pendingCommand ? <p role="status">Sending… Waiting for server confirmation.</p> : null}
      {state.phase !== 'final_betting' && own?.decision_submitted && !own.removed ? (
        <p className="text-sm text-slate-300">
          {own.wager === null ? 'You passed.' : `Your committed wager: ${own.wager}.`}
          {state.phase === 'final_reveal' && own.answer_submitted && !own.revealed
            ? ` Your accepted answer: ${own.answer?.trim() || 'Not submitted'}.`
            : ''}
        </p>
      ) : null}
      {state.phase === 'final_betting' ? (
        <div className="mx-auto w-full max-w-md space-y-3">
          <p>The question stays hidden until wagers close. Wagers and Pass cannot be changed.</p>
          {canWager ? (
            <form
              onSubmit={(event) => {
                event.preventDefault();
                if (!blocked && validWager && canSubmitFinalWager(state, userId)) {
                  emit('submit_final_wager', { amount });
                }
              }}
              className="space-y-2"
            >
              <Field
                label="Your Final wager"
                htmlFor="final-wager"
                hint={`1 to ${own?.score_before_final}`}
              >
                <Input
                  id="final-wager"
                  type="number"
                  min={1}
                  max={own?.score_before_final}
                  step={1}
                  value={wager}
                  disabled={blocked}
                  onChange={(event) => setWager(event.target.value)}
                />
              </Field>
              <div className="flex gap-2">
                <Button type="submit" disabled={blocked || !validWager}>
                  Commit wager
                </Button>
                <Button
                  type="button"
                  variant="secondary"
                  disabled={blocked}
                  onClick={() => {
                    if (canSubmitFinalWager(state, userId))
                      emit('submit_final_wager', { amount: null });
                  }}
                >
                  Pass
                </Button>
              </div>
            </form>
          ) : own?.decision_submitted && !own.removed ? (
            <p role="status">
              {own.wager === null ? 'You passed.' : `Wager accepted: ${own.wager}.`} Your decision
              is final.
            </p>
          ) : (
            <p>
              {own && !own.removed
                ? 'Wagering closed. Waiting for the server…'
                : 'Watching the Final. No wager is required from you.'}
            </p>
          )}
        </div>
      ) : null}
      {(state.phase === 'final_answering' || state.phase === 'final_reveal') && prompt ? (
        <PromptStage prompt={prompt} categoryName={currentCategoryName(state)} />
      ) : null}
      {state.phase === 'final_answering' ? (
        <div className="mx-auto w-full max-w-xl space-y-2">
          {canAnswer ? (
            <form
              className="space-y-2"
              onSubmit={(event) => {
                event.preventDefault();
                if (!blocked && canSubmitFinalAnswer(state, userId)) {
                  emit('submit_final_answer', { answer });
                }
              }}
            >
              <Field
                label="Your Final answer"
                htmlFor="final-answer"
                hint="Submit once. An empty answer is incorrect. An unsent draft does not count."
              >
                <Input
                  id="final-answer"
                  value={answer}
                  maxLength={256}
                  disabled={blocked}
                  autoComplete="off"
                  onChange={(event) => setAnswer(event.target.value)}
                />
              </Field>
              <Button type="submit" disabled={blocked}>
                Submit answer
              </Button>
            </form>
          ) : own?.answer_submitted && !own.removed ? (
            <p role="status">
              Answer accepted: {own.answer?.trim() || 'Not submitted'}. Your submission is final.
            </p>
          ) : (
            <p>
              {own?.wager && !own.removed
                ? 'Answering closed. Waiting for the server…'
                : 'Watching the Final. Answers stay private until each reveal.'}
            </p>
          )}
        </div>
      ) : null}
      {state.phase === 'final_reveal' ? (
        <div className="space-y-3 rounded border border-amber-500/40 p-3">
          <section aria-label="Correct Final answer" className="space-y-2">
            <h3 className="font-semibold text-amber-300">Correct answer</h3>
            <p>{final.correct_answer}</p>
            {final.correct_answer_media && final.correct_answer_type ? (
              <PromptMedia
                contentType={final.correct_answer_type}
                media={final.correct_answer_media}
                src={preloadedSrc(final.correct_answer_media)}
                alt={`Correct answer: ${final.correct_answer ?? ''}`}
                playbackId={`final:${state.current_prompt_id}:answer`}
              />
            ) : null}
          </section>
          {current?.revealed ? (
            <section aria-label="Current Final response" className="space-y-2">
              <h3 className="font-semibold">{current.username}</h3>
              <p>{current.answer?.trim() || 'Not submitted'}</p>
              {current.correct !== null ? (
                <p role="status">
                  {current.correct ? 'Correct' : 'Wrong'} · Wager {current.wager} ·{' '}
                  {(current.score_delta ?? 0) > 0 ? '+' : ''}
                  {current.score_delta} · Score {current.updated_score}
                </p>
              ) : (
                <p>Waiting for host judgment. Wager stays private until judgment.</p>
              )}
              {isHost ? (
                <div className="flex flex-wrap gap-2">
                  {canJudgeFinalAnswer(state, userId) ? (
                    <>
                      <Button
                        disabled={blocked}
                        onClick={() =>
                          emit('judge_final_answer', { user_id: current.user_id, correct: true })
                        }
                      >
                        Correct
                      </Button>
                      <Button
                        variant="danger"
                        disabled={blocked}
                        onClick={() =>
                          emit('judge_final_answer', { user_id: current.user_id, correct: false })
                        }
                      >
                        Wrong
                      </Button>
                    </>
                  ) : null}
                  <Button
                    disabled={blocked || !canAdvanceFinalReveal(state, userId)}
                    onClick={() => emit('advance_final_reveal', { user_id: current.user_id })}
                  >
                    {final.is_last_reveal ? 'Finish game' : 'Next'}
                  </Button>
                </div>
              ) : null}
            </section>
          ) : null}
        </div>
      ) : null}
      <ul aria-label="Final progress" className="space-y-1 text-sm text-slate-300">
        {final.players.map((player) => (
          <li key={player.user_id}>
            {player.username}:{' '}
            {player.removed
              ? 'Removed from Final'
              : state.phase === 'final_betting'
                ? player.decision_submitted
                  ? 'Decision received'
                  : 'Waiting for decision'
                : player.answer_submitted
                  ? 'Answer received'
                  : 'No answer received'}
            {player.revealed && player.user_id !== current?.user_id ? (
              <> · {player.answer?.trim() || 'Not submitted'}</>
            ) : null}
            {player.correct !== null && player.user_id !== current?.user_id ? (
              <>
                {' '}
                · {player.correct ? 'Correct' : 'Wrong'} · Wager {player.wager} ·{' '}
                {(player.score_delta ?? 0) > 0 ? '+' : ''}
                {player.score_delta} · Score {player.updated_score}
              </>
            ) : null}
          </li>
        ))}
      </ul>
    </section>
  );
};

export default FinalRoundPanel;
