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
  return (
    <Card className="p-3">
      <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-400">
        Players
      </h3>
      <ul className="space-y-1">
        <li className="flex items-center justify-between gap-2 rounded-sm bg-slate-800/60 px-2 py-1 text-sm">
          <span className="flex items-center gap-2">
            <ConnectionPill status={state.host.connection_status} />
            <span className="font-medium text-amber-300">{state.host.username}</span>
            <span className="text-xs text-slate-400">(host)</span>
          </span>
        </li>
        {sorted.map((p) => {
          const role: string[] = [];
          if (state.selecting_player_id === p.user_id) role.push('picking');
          if (state.answering_player_id === p.user_id) role.push('answering');
          if (state.attempted_player_ids.includes(p.user_id)) role.push('attempted');
          return (
            <li
              key={p.user_id}
              className={`flex items-center justify-between gap-2 rounded-sm px-2 py-1 text-sm ${
                p.is_selected
                  ? 'bg-amber-400/20 text-amber-100'
                  : p.user_id === currentUserId
                    ? 'bg-slate-800/80'
                    : 'bg-slate-900/40'
              }`}
            >
              <span className="flex min-w-0 items-center gap-2">
                <ConnectionPill status={p.connection_status} />
                <span className={`truncate ${p.is_banned ? 'line-through text-slate-500' : ''}`}>
                  {p.username}
                </span>
                {role.length ? (
                  <span className="text-xs text-slate-400">({role.join(', ')})</span>
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
