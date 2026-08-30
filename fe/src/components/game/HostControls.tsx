import Button from '@/components/ui/Button';
import type { GameLobbyState } from '@/schemas';
import {
  canAdvanceAnswerReveal,
  canJudge,
  canSelectStarter,
  canStartGame,
} from '@/services/game/phaseGuards';

interface Props {
  state: GameLobbyState;
  currentUserId: number;
  onStart: () => void;
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
    return (
      <Button fullWidth size="lg" disabled={!canStartGame(state, currentUserId)} onClick={onStart}>
        Start game
      </Button>
    );
  }
  if (state.phase === 'host_selecting_starting_player' && canSelectStarter(state, currentUserId)) {
    const eligible = state.players.filter(
      (p) => !p.is_banned && p.connection_status === 'connected',
    );
    return (
      <div className="space-y-2">
        <p className="text-sm font-semibold text-slate-300">Choose starting player</p>
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
    <div>
      <p className="mb-2 text-xs font-bold uppercase tracking-[0.18em] text-slate-400">
        Host controls
      </p>
      <div className="grid grid-cols-3 gap-2">
        <button
          type="button"
          disabled={!canJudgeAnswer}
          onClick={() => onJudge(true)}
          className="rounded-md bg-emerald-500 px-2 py-3 text-sm font-bold text-slate-950 transition-colors hover:bg-emerald-400 focus:outline-none focus:ring-2 focus:ring-amber-400 focus:ring-offset-2 focus:ring-offset-slate-950 disabled:bg-slate-800 disabled:text-slate-500"
        >
          Accept
        </button>
        <button
          type="button"
          disabled={!canJudgeAnswer}
          onClick={() => onJudge(false)}
          className="rounded-md bg-rose-600 px-2 py-3 text-sm font-bold text-white transition-colors hover:bg-rose-500 focus:outline-none focus:ring-2 focus:ring-amber-400 focus:ring-offset-2 focus:ring-offset-slate-950 disabled:bg-slate-800 disabled:text-slate-500"
        >
          Decline
        </button>
        <button
          type="button"
          disabled={!canAdvance}
          onClick={onAdvanceAnswerReveal}
          className="rounded-md bg-amber-400 px-2 py-3 text-sm font-bold text-slate-950 transition-colors hover:bg-amber-300 focus:outline-none focus:ring-2 focus:ring-amber-400 focus:ring-offset-2 focus:ring-offset-slate-950 disabled:bg-slate-800 disabled:text-slate-500"
        >
          Next
        </button>
      </div>
    </div>
  );
};

export default HostControls;
