import type { GameLobbyState } from '@/schemas';
import { sortedScoreboard } from '@/services/game/gameDerivations';

interface Props {
  state: GameLobbyState;
  currentUserId: number;
  onBan?: (userId: number) => void;
  onUnban?: (userId: number) => void;
}

const StopSignIcon = () => (
  <svg aria-hidden="true" viewBox="0 0 64 64" className="h-5 w-5 fill-current">
    <path d="m22 5 20 0 17 17 0 20-17 17-20 0L5 42 5 22Z" />
    <path d="M18 29h28v6H18z" className="fill-slate-950" />
  </svg>
);

const ScoreBoard = ({ state, currentUserId, onBan, onUnban }: Props) => {
  const sorted = sortedScoreboard(state);
  const isHost = currentUserId === state.host.user_id;
  const hostAction =
    state.phase === 'waiting_for_players' ||
    state.phase === 'host_selecting_starting_player' ||
    state.phase === 'player_answering';

  const playerTile = (
    player: GameLobbyState['players'][number],
    isActive: boolean,
  ): JSX.Element => {
    const isMuted = player.is_banned || player.connection_status === 'disconnected';
    const moderatorAction = player.is_banned ? onUnban : onBan;

    return (
      <li
        key={player.user_id}
        data-testid={`player-tile-${player.user_id}`}
        data-active={isActive || undefined}
        data-muted={isMuted || undefined}
        className={`relative flex min-h-24 min-w-0 flex-col items-center justify-center rounded-xl border px-8 py-4 text-center shadow-sm transition-colors ${
          isMuted
            ? 'border-slate-800 bg-slate-900/40 text-slate-500 opacity-70'
            : isActive
              ? 'border-amber-300 bg-amber-400/20 text-amber-50 ring-1 ring-amber-300/80'
              : 'border-slate-800 bg-slate-900/70 text-slate-100'
        }`}
      >
        <span
          className={`max-w-full truncate text-sm font-semibold sm:text-base ${
            player.is_banned ? 'line-through' : ''
          }`}
        >
          {player.username}
        </span>
        <span className="mt-1 text-lg font-bold tabular-nums">{player.score}</span>
        {isHost ? (
          <button
            type="button"
            aria-label={`${player.is_banned ? 'Unban' : 'Ban'} ${player.username}`}
            disabled={!moderatorAction}
            onClick={() => moderatorAction?.(player.user_id)}
            className={`absolute right-2 top-2 rounded p-1 transition-colors focus:outline-none focus:ring-2 focus:ring-amber-400 ${
              player.is_banned
                ? 'text-slate-500 hover:text-amber-300'
                : 'text-rose-300 hover:bg-rose-500/20 hover:text-rose-200'
            }`}
          >
            <StopSignIcon />
          </button>
        ) : player.is_banned ? (
          <span
            aria-label="Banned"
            title="Banned"
            className="absolute right-2 top-2 text-slate-500"
          >
            <StopSignIcon />
          </span>
        ) : null}
      </li>
    );
  };

  return (
    <section aria-label="Players">
      <ul className="grid grid-cols-[repeat(auto-fit,minmax(9rem,1fr))] gap-2">
        <li
          data-testid="host-player-tile"
          data-active={hostAction || undefined}
          data-muted={state.host.connection_status === 'disconnected' || undefined}
          className={`flex min-h-24 min-w-0 flex-col items-center justify-center rounded-xl border px-4 py-4 text-center shadow-sm transition-colors ${
            state.host.connection_status === 'disconnected'
              ? 'border-slate-800 bg-slate-900/40 text-slate-500 opacity-70'
              : hostAction
                ? 'border-amber-300 bg-amber-400/20 text-amber-50 ring-1 ring-amber-300/80'
                : 'border-slate-800 bg-slate-900/70 text-amber-300'
          }`}
        >
          <span className="max-w-full truncate text-sm font-semibold sm:text-base">
            {state.host.username}
          </span>
          <span
            aria-label="Host is non-scoring"
            className="mt-1 text-lg font-bold tabular-nums text-slate-400"
          >
            —
          </span>
        </li>
        {sorted.map((player) =>
          playerTile(
            player,
            player.is_selected ||
              state.selecting_player_id === player.user_id ||
              state.answering_player_id === player.user_id,
          ),
        )}
      </ul>
    </section>
  );
};

export default ScoreBoard;
