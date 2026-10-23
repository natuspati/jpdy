import { type KeyboardEvent, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import Badge from '@/components/ui/Badge';
import Button from '@/components/ui/Button';
import Spinner from '@/components/ui/Spinner';
import { useInfiniteScroll } from '@/hooks/useInfiniteScroll';
import { useDeleteLobby } from '@/hooks/useLobbies';
import type { MyLobby } from '@/schemas';
import { formatLocalDateTime } from '@/utils/formatDateTime';
import DeleteLobbyModal from './DeleteLobbyModal';

interface Props {
  lobbies: MyLobby[];
  loading: boolean;
  error: boolean;
  hasMore: boolean;
  loadingMore: boolean;
  onLoadMore: () => void;
}

const stateLabels = {
  created: 'Setup',
  waiting_start: 'Waiting for players',
  in_progress: 'In progress',
  completed: 'Completed',
} as const;

const canJoin = (lobby: MyLobby): boolean =>
  (lobby.is_owner || lobby.is_participant) &&
  (lobby.state === 'waiting_start' || lobby.state === 'in_progress');

const MyLobbyList = ({ lobbies, loading, error, hasMore, loadingMore, onLoadMore }: Props) => {
  const navigate = useNavigate();
  const sentinelRef = useInfiniteScroll(onLoadMore, hasMore && !loadingMore);
  const remove = useDeleteLobby();
  const [deleteTarget, setDeleteTarget] = useState<MyLobby | null>(null);

  const confirmDelete = async () => {
    if (!deleteTarget) return;
    await remove.mutateAsync(deleteTarget.id);
    setDeleteTarget(null);
  };

  // Live lobbies join the game; anything else opens its details.
  const open = (lobby: MyLobby) =>
    navigate(canJoin(lobby) ? `/lobby/${lobby.id}` : `/lobby/${lobby.id}/details`);
  const onRowKeyDown = (event: KeyboardEvent, lobby: MyLobby) => {
    if (event.key === 'Enter' && event.target === event.currentTarget) open(lobby);
  };

  return (
    <section className="flex min-h-0 min-w-0 flex-col gap-3">
      <h2 className="text-lg font-semibold text-slate-100">My lobbies</h2>
      {loading ? (
        <Spinner />
      ) : error ? (
        <p className="text-rose-400">Your lobbies are unavailable.</p>
      ) : (
        <div className="max-h-[28rem] min-h-0 overflow-auto rounded-lg border border-slate-800 md:max-h-none">
          <table className="min-w-full text-left text-sm">
            <thead className="sticky top-0 z-[1] bg-slate-900 text-xs uppercase tracking-wide text-slate-400">
              <tr>
                <th className="whitespace-nowrap sm:w-20 px-1.5 py-2 sm:px-3 sm:py-3">Lobby ID</th>
                <th className="px-1.5 py-2 sm:px-3 sm:py-3">Host</th>
                <th className="px-1.5 py-2 sm:px-3 sm:py-3">Players</th>
                <th className="whitespace-nowrap px-1.5 py-2 sm:px-3 sm:py-3">State</th>
                <th className="hidden whitespace-nowrap px-3 py-3 sm:table-cell">Created at</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800 bg-slate-950/40">
              {lobbies.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-3 py-4 text-center text-slate-400">
                    No owned or joined lobbies yet.
                  </td>
                </tr>
              ) : null}
              {lobbies.map((lobby) => {
                const live = canJoin(lobby);
                return (
                  <tr
                    key={lobby.id}
                    tabIndex={0}
                    aria-label={`${live ? 'Join' : 'Show details of'} lobby ${lobby.id}`}
                    className={`cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-amber-400 ${
                      live ? 'bg-amber-400/10 hover:bg-amber-400/20' : 'hover:bg-slate-900'
                    }`}
                    onClick={() => open(lobby)}
                    onKeyDown={(event) => onRowKeyDown(event, lobby)}
                  >
                    <td
                      className={`whitespace-nowrap border-l-4 px-1.5 py-2 sm:px-3 sm:py-3 font-semibold ${
                        live
                          ? 'border-amber-400 text-amber-300'
                          : 'border-transparent text-slate-100'
                      }`}
                    >
                      #{lobby.id}
                    </td>
                    <td className="max-w-24 truncate px-1.5 py-2 text-slate-300 sm:max-w-none sm:px-3 sm:py-3">
                      {lobby.host_username ?? '(deleted user)'}
                    </td>
                    <td className="px-1.5 py-2 sm:px-3 sm:py-3 text-slate-300">
                      {lobby.player_count}
                    </td>
                    <td className="whitespace-nowrap px-1.5 py-2 sm:px-3 sm:py-3">
                      <div className="flex items-center gap-2">
                        <span
                          className="group relative inline-flex"
                          title={
                            lobby.state === 'waiting_start' ? stateLabels.waiting_start : undefined
                          }
                        >
                          <Badge tone={lobby.state === 'in_progress' ? 'warning' : 'info'}>
                            {lobby.state === 'waiting_start'
                              ? 'Waiting...'
                              : stateLabels[lobby.state]}
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
                        {lobby.is_owner ? (
                          <Button
                            aria-label={`Delete lobby ${lobby.id}`}
                            title="Delete lobby"
                            size="icon"
                            variant="danger"
                            onClick={(event) => {
                              event.stopPropagation();
                              setDeleteTarget(lobby);
                            }}
                          >
                            X
                          </Button>
                        ) : null}
                      </div>
                    </td>
                    <td className="hidden whitespace-nowrap px-3 py-3 text-slate-300 sm:table-cell">
                      {formatLocalDateTime(lobby.created_at)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {loadingMore ? (
            <div className="flex justify-center py-3">
              <Spinner />
            </div>
          ) : null}
          <div ref={sentinelRef} aria-hidden className="h-px" />
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
