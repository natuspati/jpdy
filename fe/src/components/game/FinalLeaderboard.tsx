import Card from '@/components/ui/Card';
import type { GameLobbyState } from '@/schemas';
import { sortedScoreboard } from '@/services/game/gameDerivations';

const FinalLeaderboard = ({ state }: { state: GameLobbyState }) => {
  const sorted = sortedScoreboard(state);
  return (
    <Card className="space-y-3">
      <h2 className="text-center text-xl font-bold">Final scores</h2>
      {sorted.length === 0 ? (
        <p className="text-center text-sm text-slate-400">No players finished this game.</p>
      ) : (
        <ol className="space-y-2">
          {sorted.map((p, i) => (
            <li
              key={p.user_id}
              className={`flex items-center justify-between rounded-md p-2 ${
                i === 0 ? 'bg-amber-400/20' : 'bg-slate-800/60'
              }`}
            >
              <span className="flex items-center gap-2">
                <span className="w-6 text-right text-slate-400">{i + 1}.</span>
                <span className={i === 0 ? 'font-bold text-amber-200' : ''}>{p.username}</span>
              </span>
              <span className="tabular-nums">{p.score}</span>
            </li>
          ))}
        </ol>
      )}
      <p className="text-center text-xs text-slate-400">
        Host: <span className="text-amber-300">{state.host.username}</span> (non-scoring)
      </p>
    </Card>
  );
};

export default FinalLeaderboard;
