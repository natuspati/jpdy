import { type FC, type ReactNode, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import Badge from '@/components/ui/Badge';
import Button from '@/components/ui/Button';
import Spinner from '@/components/ui/Spinner';
import { useDeleteLobby } from '@/hooks/useLobbies';
import type { MyLobby } from '@/schemas';
import { formatLocalDateTime } from '@/utils/formatDateTime';
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

interface LobbyActionButtonProps {
  label: string;
  variant: 'primary' | 'secondary' | 'danger';
  onClick: () => void;
  children: ReactNode;
}

const LobbyActionButton: FC<LobbyActionButtonProps> = ({ label, variant, onClick, children }) => (
  <div className="group relative">
    <Button aria-label={label} size="icon" title={label} variant={variant} onClick={onClick}>
      {children}
    </Button>
    <span
      role="tooltip"
      className="pointer-events-none absolute bottom-full left-1/2 z-10 mb-2 -translate-x-1/2 whitespace-nowrap rounded bg-slate-700 px-2 py-1 text-xs font-medium text-slate-50 opacity-0 shadow transition-opacity group-hover:opacity-100 group-focus-within:opacity-100"
    >
      {label}
    </span>
  </div>
);

const canJoin = (lobby: MyLobby): boolean =>
  (lobby.is_owner || lobby.is_participant) &&
  (lobby.state === 'waiting_start' || lobby.state === 'in_progress');

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
                <th className="w-20 whitespace-nowrap px-3 py-3">Lobby ID</th>
                <th className="px-3 py-3">Host</th>
                <th className="px-3 py-3">Players</th>
                <th className="whitespace-nowrap px-3 py-3">State</th>
                <th className="whitespace-nowrap px-3 py-3">Created at</th>
                <th className="w-28 whitespace-nowrap px-3 py-3">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800 bg-slate-950/40">
              {lobbies.map((lobby) => (
                <tr key={lobby.id}>
                  <td className="whitespace-nowrap px-3 py-3 font-semibold text-slate-100">
                    #{lobby.id}
                  </td>
                  <td className="px-3 py-3 text-slate-300">
                    {lobby.host_username ?? '(deleted user)'}
                  </td>
                  <td className="px-3 py-3 text-slate-300">{lobby.player_count}</td>
                  <td className="whitespace-nowrap px-3 py-3">
                    <span
                      className="group relative inline-flex"
                      title={
                        lobby.state === 'waiting_start' ? stateLabels.waiting_start : undefined
                      }
                    >
                      <Badge tone={lobby.state === 'in_progress' ? 'warning' : 'info'}>
                        {lobby.state === 'waiting_start' ? 'Waiting...' : stateLabels[lobby.state]}
                      </Badge>
                      {lobby.state === 'waiting_start' ? (
                        <span
                          role="tooltip"
                          className="pointer-events-none absolute bottom-full left-1/2 z-10 mb-2 -translate-x-1/2 whitespace-nowrap rounded bg-slate-700 px-2 py-1 text-xs font-medium text-slate-50 opacity-0 shadow transition-opacity group-hover:opacity-100"
                        >
                          {stateLabels.waiting_start}
                        </span>
                      ) : null}
                    </span>
                  </td>
                  <td className="whitespace-nowrap px-3 py-3 text-slate-300">
                    {formatLocalDateTime(lobby.created_at)}
                  </td>
                  <td className="w-28 whitespace-nowrap px-3 py-3">
                    <div className="flex flex-nowrap gap-1">
                      {canJoin(lobby) ? (
                        <LobbyActionButton
                          label="Join"
                          variant="primary"
                          onClick={() => navigate(`/lobby/${lobby.id}`)}
                        >
                          J
                        </LobbyActionButton>
                      ) : null}
                      <LobbyActionButton
                        label="Show details"
                        variant="secondary"
                        onClick={() => navigate(`/lobby/${lobby.id}/details`)}
                      >
                        D
                      </LobbyActionButton>
                      {lobby.is_owner ? (
                        <LobbyActionButton
                          label="Delete"
                          variant="danger"
                          onClick={() => setDeleteTarget(lobby)}
                        >
                          X
                        </LobbyActionButton>
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
