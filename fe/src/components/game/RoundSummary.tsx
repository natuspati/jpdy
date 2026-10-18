import Button from '@/components/ui/Button';
import type { GameLobbyState } from '@/schemas';
import { ROUND_SUMMARY_TIME_SECONDS } from '@/services/game/gameTiming';
import { canAdvanceRound } from '@/services/game/phaseGuards';
import { RoundStandings } from './RoundRecap';
import TimerBar from './TimerBar';

interface Props {
  state: GameLobbyState;
  currentUserId: number;
  onAdvance: () => void;
}

const RoundSummary = ({ state, currentUserId, onAdvance }: Props) => {
  const result = state.round_results[state.round_results.length - 1];
  const finishedRound = result?.round_number ?? state.current_round;
  const nextIsFinal = state.categories.some(
    (category) => category.round_number === finishedRound + 1 && category.kind === 'final',
  );
  return (
    <section aria-label="Round summary" className="mx-auto w-full max-w-xl space-y-3">
      <h2 className="text-center text-xl font-bold text-amber-300">
        Round {finishedRound} complete
      </h2>
      <RoundStandings
        standings={(result?.scores ?? []).map((score) => ({
          key: score.user_id,
          username: score.username,
          score: score.score,
          scoreDelta: score.score_delta,
          isBanned: score.is_banned,
        }))}
      />
      <TimerBar deadline={state.timer_deadline} totalSeconds={ROUND_SUMMARY_TIME_SECONDS} />
      {canAdvanceRound(state, currentUserId) ? (
        <Button fullWidth size="lg" onClick={onAdvance}>
          {nextIsFinal ? 'Start Final' : `Start round ${finishedRound + 1}`}
        </Button>
      ) : (
        <p className="text-center text-sm text-slate-400">
          {nextIsFinal ? 'Final starts automatically' : 'Next round starts automatically'}
        </p>
      )}
    </section>
  );
};

export default RoundSummary;
