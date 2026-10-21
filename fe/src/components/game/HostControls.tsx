import Button from '@/components/ui/Button';
import JudgeButtons from './JudgeButtons';
import type { GameLobbyState } from '@/schemas';
import {
  canAdvanceAnswerReveal,
  canJudge,
  canSelectStarter,
  canStartGame,
  playersStillLoading,
} from '@/services/game/phaseGuards';

interface Props {
  state: GameLobbyState;
  currentUserId: number;
  onStart: (force?: boolean) => void;
  onSelectStarter: (userId: number) => void;
  onAdvanceAnswerReveal: () => void;
  onJudge: (correct: boolean) => void;
}

const HostControls = ({
  state,
  currentUserId,
  onStart,
  onSelectStarter,
  onAdvanceAnswerReveal,
  onJudge,
}: Props) => {
  const canJudgeAnswer = canJudge(state, currentUserId);
  const canAdvance = canAdvanceAnswerReveal(state, currentUserId);
  if (state.phase === 'waiting_for_players') {
    const loading = playersStillLoading(state);
    return (
      <div className="mx-auto w-full max-w-xs space-y-2 sm:max-w-md">
        <Button
          fullWidth
          size="lg"
          disabled={!canStartGame(state, currentUserId)}
          onClick={() => onStart()}
        >
          Start game
        </Button>
        {loading > 0 ? (
          <div className="flex items-center justify-between gap-2 text-sm text-slate-400">
            <span>{loading} loading…</span>
            <Button
              size="sm"
              variant="secondary"
              disabled={!canStartGame(state, currentUserId, true)}
              onClick={() => onStart(true)}
            >
              Start anyway
            </Button>
          </div>
        ) : null}
      </div>
    );
  }
  if (state.phase === 'host_selecting_starting_player' && canSelectStarter(state, currentUserId)) {
    const eligible = state.players.filter(
      (p) => !p.is_banned && p.connection_status === 'connected',
    );
    return (
      <div className="mx-auto w-full max-w-xs space-y-2 sm:max-w-md">
        <p className="text-center text-sm font-semibold text-slate-300">Choose starting player</p>
        {eligible.length === 0 ? (
          <p className="text-sm text-slate-400">
            Waiting for a player to reconnect or be unbanned.
          </p>
        ) : (
          <ul className="space-y-1">
            {eligible.map((p) => (
              <li key={p.user_id}>
                <Button fullWidth variant="secondary" onClick={() => onSelectStarter(p.user_id)}>
                  {p.username}
                </Button>
              </li>
            ))}
          </ul>
        )}
      </div>
    );
  }

  return (
    <div className="mx-auto w-full max-w-xs sm:max-w-md">
      <JudgeButtons
        canJudge={canJudgeAnswer}
        canAdvance={canAdvance}
        onJudge={onJudge}
        onNext={onAdvanceAnswerReveal}
      />
    </div>
  );
};

export default HostControls;
