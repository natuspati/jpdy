import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

import RoundRecap from '@/components/game/RoundRecap';
import Button from '@/components/ui/Button';
import Card from '@/components/ui/Card';
import Spinner from '@/components/ui/Spinner';
import DeleteLobbyModal from '@/components/lobby/DeleteLobbyModal';
import { useDeleteLobby, useLobby } from '@/hooks/useLobbies';

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
  const remove = useDeleteLobby();
  const [confirmingDelete, setConfirmingDelete] = useState(false);

  const handleDelete = async () => {
    if (!data) return;
    await remove.mutateAsync(data.id);
    navigate('/');
  };

  if (lobbyIdSafe === undefined) return <p className="text-rose-400">Invalid lobby id.</p>;
  if (isLoading) return <Spinner />;
  if (isError || !data) return <p className="text-rose-400">Lobby details are unavailable.</p>;

  return (
    <Card className="mx-auto max-w-2xl space-y-5">
      <div className="flex items-center gap-3">
        <div className="group relative">
          <Button
            aria-label="Back to lobbies"
            size="icon"
            title="Back to lobbies"
            variant="secondary"
            onClick={() => navigate('/')}
          >
            <span aria-hidden="true">←</span>
          </Button>
          <span
            role="tooltip"
            className="pointer-events-none absolute left-0 top-full z-10 mt-2 whitespace-nowrap rounded bg-slate-700 px-2 py-1 text-xs font-medium text-slate-50 opacity-0 shadow transition-opacity group-hover:opacity-100 group-focus-within:opacity-100"
          >
            Back to lobbies
          </span>
        </div>
        <h1 className="flex-1 text-2xl font-bold text-slate-50">Lobby #{data.id}</h1>
        {data.is_owner ? (
          <Button variant="danger" size="sm" onClick={() => setConfirmingDelete(true)}>
            Delete lobby
          </Button>
        ) : null}
      </div>
      <dl className="grid grid-cols-2 gap-4 text-sm sm:grid-cols-4">
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
      <div>
        {data.rounds.length === 0 ? (
          <p className="text-sm text-slate-400">No categories attached.</p>
        ) : (
          <div className="space-y-3">
            {data.rounds.map((round) => (
              <div
                key={round.round_number}
                className="rounded border border-slate-800 bg-slate-950/50 p-3"
              >
                <RoundRecap
                  roundNumber={round.round_number}
                  isFinal={round.kind === 'final'}
                  categoryNames={round.categories.map((category) => category.name)}
                  standings={
                    round.results?.map((result) => ({
                      key: `${result.user_id ?? 'deleted'}-${result.username}`,
                      username: result.username,
                      score: result.score,
                      scoreDelta: result.score_delta,
                      isBanned: result.is_banned,
                    })) ?? null
                  }
                />
              </div>
            ))}
          </div>
        )}
      </div>
      <DeleteLobbyModal
        lobby={confirmingDelete ? data : null}
        pending={remove.isPending}
        onClose={() => setConfirmingDelete(false)}
        onConfirm={() => void handleDelete()}
      />
    </Card>
  );
};

export default LobbyDetailsPage;
