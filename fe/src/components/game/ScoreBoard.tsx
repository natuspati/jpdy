import Card from '@/components/ui/Card';
import ConnectionPill from './ConnectionPill';
import type { GameLobbyState } from '@/schemas';
import { sortedScoreboard } from '@/services/game/gameDerivations';

interface Props {
  state: GameLobbyState;
  currentUserId: number;
  onBan?: (userId: number) => void;
  onUnban?: (userId: number) => void;
}

const ScoreBoard = ({ state, currentUserId, onBan, onUnban }: Props) => {
  const sorted = sortedScoreboard(state);
  const isHost = currentUserId === state.host.user_id;
  const hostAction =
    state.phase === 'waiting_for_players' ||
    state.phase === 'host_selecting_starting_player' ||
    state.phase === 'player_answering';
  return (
    <Card className="p-3">
      <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-400">Players</h3>
      <ul className="space-y-1">
        <li
          className={`flex items-center justify-between gap-2 rounded-md px-3 py-2 text-sm ${
            hostAction
              ? 'ring-1 ring-amber-300/80 bg-amber-400/20 text-amber-50'
              : 'bg-slate-800/60'
          }`}
        >
          <span className="flex items-center gap-2">
            <ConnectionPill status={state.host.connection_status} />
            <span className="font-medium text-amber-300">{state.host.username}</span>
            <span className="text-xs text-slate-400">HOST</span>
            {hostAction ? (
              <span className="rounded bg-amber-300 px-1.5 py-0.5 text-[0.625rem] font-black tracking-wide text-slate-950">
                HOST ACTION
              </span>
            ) : null}
          </span>
        </li>
        {sorted.map((p) => {
          const isAnswerer = state.answering_player_id === p.user_id;
          const isSelector = state.selecting_player_id === p.user_id;
          const attempted = state.attempted_player_ids.includes(p.user_id);
          const labels = [
            ...(isAnswerer ? ['ANSWERING'] : []),
            ...(isSelector && !isAnswerer ? ['SELECTING'] : []),
            ...(attempted ? ['ATTEMPTED'] : []),
            ...(p.is_banned ? ['BANNED'] : []),
            ...(p.connection_status === 'disconnected' ? ['DISCONNECTED'] : []),
          ];
          return (
            <li
              key={p.user_id}
              className={`flex items-center justify-between gap-2 rounded-md px-3 py-2 text-sm ${
                isAnswerer
                  ? 'animate-pulse ring-2 ring-amber-300 bg-amber-400/30 text-amber-50'
                  : isSelector
                    ? 'ring-1 ring-amber-300/70 bg-amber-400/15 text-amber-100'
                    : p.user_id === currentUserId
                      ? 'bg-slate-800/80'
                      : 'bg-slate-900/40'
              }`}
            >
              <span className="flex min-w-0 items-center gap-2">
                <ConnectionPill status={p.connection_status} />
                <span
                  className={`truncate font-medium ${p.is_banned ? 'line-through text-slate-500' : ''}`}
                >
                  {p.username}
                </span>
                {labels.length ? (
                  <span className="flex flex-wrap gap-1">
                    {labels.map((label) => (
                      <span
                        key={label}
                        className={`rounded px-1.5 py-0.5 text-[0.625rem] font-black tracking-wide ${
                          label === 'ANSWERING'
                            ? 'bg-amber-300 text-slate-950'
                            : label === 'SELECTING'
                              ? 'bg-amber-300/80 text-slate-950'
                              : label === 'BANNED'
                                ? 'bg-rose-500/30 text-rose-200'
                                : 'bg-slate-700 text-slate-300'
                        }`}
                      >
                        {label}
                      </span>
                    ))}
                  </span>
                ) : null}
              </span>
              <span className="flex shrink-0 items-center gap-2">
                <span className="tabular-nums text-slate-100">{p.score}</span>
                {isHost && p.user_id !== currentUserId ? (
                  p.is_banned ? (
                    <button
                      className="text-xs text-amber-300 hover:underline"
                      onClick={() => onUnban?.(p.user_id)}
                    >
                      unban
                    </button>
                  ) : (
                    <button
                      className="text-xs text-rose-300 hover:underline"
                      onClick={() => onBan?.(p.user_id)}
                    >
                      ban
                    </button>
                  )
                ) : null}
              </span>
            </li>
          );
        })}
      </ul>
    </Card>
  );
};

export default ScoreBoard;
