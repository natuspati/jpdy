import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import Badge from '@/components/ui/Badge';
import Button from '@/components/ui/Button';
import Spinner from '@/components/ui/Spinner';
import { useDeleteLobby } from '@/hooks/useLobbies';
import type { MyLobby } from '@/schemas';
import DeleteLobbyModal from './DeleteLobbyModal';

interface Props {
  lobbies: MyLobby[];
  loading: boolean;
  error: boolean;
}

const stateLabels = {
  created: 'Setup',
  waiting_start: 'Waiting for players',
  in_progress: 'In progress',
  completed: 'Completed',
} as const;

const MyLobbyList = ({ lobbies, loading, error }: Props) => {
  const navigate = useNavigate();
  const remove = useDeleteLobby();
  const [deleteTarget, setDeleteTarget] = useState<MyLobby | null>(null);

  const confirmDelete = async () => {
    if (!deleteTarget) return;
    await remove.mutateAsync(deleteTarget.id);
    setDeleteTarget(null);
  };

  return (
    <section className="min-w-0 space-y-3">
      <h2 className="text-lg font-semibold text-slate-100">My lobbies</h2>
      {loading ? (
        <Spinner />
      ) : error ? (
        <p className="text-rose-400">Your lobbies are unavailable.</p>
      ) : lobbies.length === 0 ? (
        <p className="text-slate-400">No owned or joined lobbies yet.</p>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-slate-800">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-slate-900 text-xs uppercase tracking-wide text-slate-400">
              <tr>
                <th className="px-3 py-3">Lobby ID</th>
                <th className="px-3 py-3">Host</th>
                <th className="px-3 py-3">Players</th>
                <th className="px-3 py-3">State</th>
                <th className="px-3 py-3">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800 bg-slate-950/40">
              {lobbies.map((lobby) => (
                <tr key={lobby.id}>
                  <td className="px-3 py-3 font-semibold text-slate-100">#{lobby.id}</td>
                  <td className="px-3 py-3 text-slate-300">
                    {lobby.host_username ?? '(deleted user)'}
                  </td>
                  <td className="px-3 py-3 text-slate-300">{lobby.player_count}</td>
                  <td className="px-3 py-3">
                    <Badge tone={lobby.state === 'in_progress' ? 'warning' : 'info'}>
                      {stateLabels[lobby.state]}
                    </Badge>
                  </td>
                  <td className="px-3 py-3">
                    <div className="flex flex-wrap gap-2">
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => navigate(`/lobby/${lobby.id}/details`)}
                      >
                        Show details
                      </Button>
                      {lobby.is_owner ? (
                        <Button size="sm" variant="danger" onClick={() => setDeleteTarget(lobby)}>
                          Delete
                        </Button>
                      ) : null}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <DeleteLobbyModal
        lobby={deleteTarget}
        pending={remove.isPending}
        onClose={() => setDeleteTarget(null)}
        onConfirm={() => void confirmDelete()}
      />
    </section>
  );
};

export default MyLobbyList;
