import { type FC, useCallback, useState } from 'react';

import Badge from '@/components/ui/Badge';
import Button from '@/components/ui/Button';
import ConfirmModal from '@/components/ui/ConfirmModal';
import Spinner from '@/components/ui/Spinner';
import { useAdminUsers, useDeleteUser, usePromoteUser } from '@/hooks/useAdmin';
import { useAuth } from '@/hooks/useAuth';
import { useDebouncedValue } from '@/hooks/useDebouncedValue';
import { useInfiniteScroll } from '@/hooks/useInfiniteScroll';
import type { AdminUser, AdminUserSortEnum } from '@/schemas';
import { formatLocalDateTime } from '@/utils/formatDateTime';
import AdminSection from './AdminSection';
import {
  type AdminUserFilters,
  DEFAULT_ADMIN_USER_FILTERS,
  toAdminUserSearch,
} from './adminUserFilters';
import SortHeader from './SortHeader';
import UserFilterBar from './UserFilterBar';

const SEARCH_DEBOUNCE_MS = 300;

const StarIcon: FC = () => (
  <svg aria-hidden="true" viewBox="0 0 24 24" fill="currentColor" className="h-4 w-4">
    <path d="M12 2l3.09 6.26L22 9.27l-5 4.87L18.18 21 12 17.77 5.82 21 7 14.14 2 9.27l6.91-1.01z" />
  </svg>
);

const CrossIcon: FC = () => (
  <svg
    aria-hidden="true"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeLinecap="round"
    strokeWidth="3"
    className="h-4 w-4"
  >
    <path d="M6 6l12 12M18 6L6 18" />
  </svg>
);

const UserManagement = () => {
  const { userId } = useAuth();
  const [filters, setFilters] = useState<AdminUserFilters>(DEFAULT_ADMIN_USER_FILTERS);
  const [sort, setSort] = useState<AdminUserSortEnum | null>(null);
  const debouncedUsername = useDebouncedValue(filters.username, SEARCH_DEBOUNCE_MS);
  const users = useAdminUsers(toAdminUserSearch({ ...filters, username: debouncedUsername }, sort));
  const { fetchNextPage, hasNextPage, isFetchingNextPage } = users;
  const loadMore = useCallback(() => void fetchNextPage(), [fetchNextPage]);
  const sentinelRef = useInfiniteScroll(loadMore, hasNextPage && !isFetchingNextPage);
  const promote = usePromoteUser();
  const remove = useDeleteUser();
  const [promoteTarget, setPromoteTarget] = useState<AdminUser | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<AdminUser | null>(null);

  const confirmPromote = async () => {
    if (!promoteTarget) return;
    await promote.mutateAsync(promoteTarget.id).catch(() => undefined);
    setPromoteTarget(null);
  };
  const confirmDelete = async () => {
    if (!deleteTarget) return;
    await remove.mutateAsync(deleteTarget.id).catch(() => undefined);
    setDeleteTarget(null);
  };

  return (
    <AdminSection title="Users" actions={<UserFilterBar value={filters} onChange={setFilters} />}>
      {users.isLoading ? (
        <div className="flex justify-center p-4">
          <Spinner />
        </div>
      ) : users.isError ? (
        <p className="p-4 text-rose-400">Users are unavailable.</p>
      ) : (
        <>
          <table className="min-w-full text-left text-sm">
            <thead className="sticky top-0 z-[1] bg-slate-900 text-xs uppercase tracking-wide text-slate-400">
              <tr>
                <SortHeader
                  column="username"
                  label="User"
                  sort={sort}
                  onChange={setSort}
                  className="px-1.5 py-2 sm:px-3 sm:py-3"
                />
                <SortHeader
                  column="role"
                  label="Role"
                  sort={sort}
                  onChange={setSort}
                  className="px-1.5 py-2 sm:px-3 sm:py-3"
                />
                <SortHeader
                  column="created_at"
                  label="Registered"
                  sort={sort}
                  onChange={setSort}
                  className="hidden whitespace-nowrap px-3 py-3 sm:table-cell"
                />
                <SortHeader
                  column="lobbies_played"
                  label="Played"
                  sort={sort}
                  onChange={setSort}
                  className="hidden px-3 py-3 sm:table-cell"
                />
                <SortHeader
                  column="lobbies_hosted"
                  label="Hosted"
                  sort={sort}
                  onChange={setSort}
                  className="hidden px-3 py-3 sm:table-cell"
                />
                <th className="px-1.5 py-2 sm:px-3 sm:py-3">
                  <span className="sr-only">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800 bg-slate-950/40">
              {(users.data ?? []).length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-3 py-4 text-center text-slate-400">
                    No users match.
                  </td>
                </tr>
              ) : null}
              {(users.data ?? []).map((user) => {
                const isAdmin = user.role === 'admin';
                return (
                  <tr key={user.id}>
                    <td className="max-w-28 truncate px-1.5 py-2 font-medium text-slate-100 sm:max-w-none sm:px-3 sm:py-3">
                      {user.username}
                    </td>
                    <td className="px-1.5 py-2 sm:px-3 sm:py-3">
                      <Badge tone={isAdmin ? 'warning' : 'neutral'}>{user.role}</Badge>
                    </td>
                    <td className="hidden whitespace-nowrap px-3 py-3 text-slate-300 sm:table-cell">
                      {formatLocalDateTime(user.created_at)}
                    </td>
                    <td className="hidden px-3 py-3 text-slate-300 sm:table-cell">
                      {user.lobbies_played}
                    </td>
                    <td className="hidden px-3 py-3 text-slate-300 sm:table-cell">
                      {user.lobbies_hosted}
                    </td>
                    <td className="px-1.5 py-2 sm:px-3 sm:py-3">
                      <div className="flex justify-end gap-2">
                        {isAdmin ? null : (
                          <Button
                            size="icon"
                            variant="secondary"
                            aria-label={`Promote ${user.username}`}
                            title="Promote"
                            onClick={() => setPromoteTarget(user)}
                          >
                            <StarIcon />
                          </Button>
                        )}
                        {isAdmin || user.id === userId ? null : (
                          <Button
                            size="icon"
                            variant="danger"
                            aria-label={`Delete ${user.username}`}
                            title="Delete"
                            onClick={() => setDeleteTarget(user)}
                          >
                            <CrossIcon />
                          </Button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {isFetchingNextPage ? (
            <div className="flex justify-center py-3">
              <Spinner />
            </div>
          ) : null}
          <div ref={sentinelRef} aria-hidden className="h-px" />
        </>
      )}
      <ConfirmModal
        open={promoteTarget !== null}
        title="Promote to admin"
        message={`Make ${promoteTarget?.username ?? ''} an admin? There is no demote.`}
        confirmLabel="Promote"
        pending={promote.isPending}
        onClose={() => setPromoteTarget(null)}
        onConfirm={() => void confirmPromote()}
      />
      <ConfirmModal
        open={deleteTarget !== null}
        title="Delete user"
        message={`Delete ${deleteTarget?.username ?? ''}? Their unfinished lobbies are deleted too; completed lobbies stay as history.`}
        confirmLabel="Delete"
        pending={remove.isPending}
        onClose={() => setDeleteTarget(null)}
        onConfirm={() => void confirmDelete()}
      />
    </AdminSection>
  );
};

export default UserManagement;
