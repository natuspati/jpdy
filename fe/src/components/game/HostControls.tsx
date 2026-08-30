import Button from '@/components/ui/Button';
import Card from '@/components/ui/Card';
import type { GameLobbyState } from '@/schemas';
import {
  canAdvanceAnswerReveal,
  canSelectStarter,
  canStartGame,
} from '@/services/game/phaseGuards';

interface Props {
  state: GameLobbyState;
  currentUserId: number;
  onStart: () => void;
  onSelectStarter: (userId: number) => void;
  onAdvanceAnswerReveal: () => void;
}

const HostControls = ({
  state,
  currentUserId,
  onStart,
  onSelectStarter,
  onAdvanceAnswerReveal,
}: Props) => {
  if (state.phase === 'waiting_for_players') {
    const eligible = state.players.filter(
      (p) => !p.is_banned && p.connection_status === 'connected',
    );
    return (
      <Card className="space-y-3">
        <p className="text-sm text-slate-300">
          {eligible.length === 0
            ? 'Waiting for at least one connected player…'
            : `${eligible.length} player${eligible.length === 1 ? '' : 's'} ready`}
        </p>
        <Button
          fullWidth
          size="lg"
          disabled={!canStartGame(state, currentUserId)}
          onClick={onStart}
        >
          Start game
        </Button>
      </Card>
    );
  }
  if (state.phase === 'host_selecting_starting_player' && canSelectStarter(state, currentUserId)) {
    const eligible = state.players.filter(
      (p) => !p.is_banned && p.connection_status === 'connected',
    );
    return (
      <Card className="space-y-2">
        <p className="text-sm font-semibold text-slate-300">Choose next player</p>
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
      </Card>
    );
  }
  if (canAdvanceAnswerReveal(state, currentUserId)) {
    return (
      <Card className="space-y-3">
        <p className="text-sm text-slate-300">
          The answer is visible. Advance whenever everyone is ready.
        </p>
        <Button fullWidth size="lg" onClick={onAdvanceAnswerReveal}>
          Next prompt
        </Button>
      </Card>
    );
  }
  return null;
};

export default HostControls;
