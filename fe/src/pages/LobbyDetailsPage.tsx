import { useNavigate, useParams } from 'react-router-dom';

import Button from '@/components/ui/Button';
import Card from '@/components/ui/Card';
import Spinner from '@/components/ui/Spinner';
import { useLobby } from '@/hooks/useLobbies';

const stateLabels = {
  created: 'Setup',
  waiting_start: 'Waiting for players',
  in_progress: 'In progress',
  completed: 'Completed',
} as const;

const LobbyDetailsPage = () => {
  const { id } = useParams<{ id: string }>();
  const lobbyId = id ? Number(id) : undefined;
  const lobbyIdSafe = lobbyId !== undefined && !Number.isNaN(lobbyId) ? lobbyId : undefined;
  const navigate = useNavigate();
  const { data, isLoading, isError } = useLobby(lobbyIdSafe);

  if (lobbyIdSafe === undefined) return <p className="text-rose-400">Invalid lobby id.</p>;
  if (isLoading) return <Spinner />;
  if (isError || !data) return <p className="text-rose-400">Lobby details are unavailable.</p>;

  return (
    <Card className="mx-auto max-w-2xl space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm uppercase tracking-wide text-slate-400">Lobby details</p>
          <h1 className="text-2xl font-bold text-slate-50">Lobby #{data.id}</h1>
        </div>
        <Button variant="secondary" onClick={() => navigate('/')}>
          Back to lobbies
        </Button>
      </div>
      <dl className="grid grid-cols-1 gap-4 text-sm sm:grid-cols-2">
        <div>
          <dt className="text-slate-400">Host</dt>
          <dd className="mt-1 font-medium text-slate-100">
            {data.owner?.username ?? '(deleted user)'}
          </dd>
        </div>
        <div>
          <dt className="text-slate-400">State</dt>
          <dd className="mt-1 font-medium text-slate-100">{stateLabels[data.state]}</dd>
        </div>
        <div>
          <dt className="text-slate-400">Players</dt>
          <dd className="mt-1 font-medium text-slate-100">
            {data.player_count === null ? 'Unavailable' : data.player_count}
          </dd>
        </div>
        <div>
          <dt className="text-slate-400">Categories</dt>
          <dd className="mt-1 font-medium text-slate-100">{data.prompt_categories.length}</dd>
        </div>
      </dl>
      <div>
        <h2 className="mb-2 font-semibold text-slate-100">Category list</h2>
        {data.prompt_categories.length === 0 ? (
          <p className="text-sm text-slate-400">No categories attached.</p>
        ) : (
          <ul className="space-y-2">
            {data.prompt_categories.map((category) => (
              <li key={category.id} className="rounded border border-slate-800 bg-slate-950/50 p-3">
                {category.name}
              </li>
            ))}
          </ul>
        )}
      </div>
      {data.final_rankings ? (
        <div>
          <h2 className="mb-2 font-semibold text-slate-100">Final rankings</h2>
          {data.final_rankings.length === 0 ? (
            <p className="text-sm text-slate-400">No players finished this game.</p>
          ) : (
            <div className="overflow-x-auto rounded border border-slate-800">
              <table className="min-w-full text-left text-sm">
                <thead className="bg-slate-900 text-xs uppercase tracking-wide text-slate-400">
                  <tr>
                    <th className="px-3 py-2">Rank</th>
                    <th className="px-3 py-2">Player</th>
                    <th className="px-3 py-2">Score</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800 bg-slate-950/40">
                  {data.final_rankings.map((player) => (
                    <tr key={`${player.user_id ?? 'deleted'}-${player.username}`}>
                      <td className="px-3 py-2 text-slate-200">{player.rank}</td>
                      <td className="px-3 py-2 text-slate-200">
                        {player.username}
                        {player.is_banned ? (
                          <span className="ml-2 text-xs font-medium text-rose-300">(banned)</span>
                        ) : null}
                      </td>
                      <td className="px-3 py-2 text-slate-200">{player.final_score}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      ) : null}
      <p className="text-sm text-slate-400">
        This view is lobby metadata only. It does not open a game connection or provide spectator
        access.
      </p>
    </Card>
  );
};

export default LobbyDetailsPage;
