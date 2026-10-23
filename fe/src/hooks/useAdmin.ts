import {
  keepPreviousData,
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query';

import {
  type AdminUserSearch,
  deleteUser,
  getCategoryStats,
  getGameStats,
  getServerStatus,
  promoteUser,
  searchAdminUsers,
} from '@/api/admin';
import { ApiError } from '@/api/errors';
import { queryKeys } from '@/api/queryKeys';
import { toastError, toastSuccess } from '@/store/toastStore';
import { flattenPages, nextPageParam } from '@/utils/pagination';

export const ADMIN_USERS_PAGE_SIZE = 30;
export const CATEGORY_STATS_PAGE_SIZE = 30;
const ADMIN_POLL_MS = 10_000;

/** Users matching the filters, loaded page by page; a different filter set starts a new list. */
export function useAdminUsers(filters: AdminUserSearch) {
  return useInfiniteQuery({
    queryKey: queryKeys.admin.users({ ...filters }),
    queryFn: ({ pageParam }) => searchAdminUsers(filters, pageParam, ADMIN_USERS_PAGE_SIZE),
    initialPageParam: 0,
    getNextPageParam: nextPageParam,
    select: ({ pages }) => flattenPages(pages),
    placeholderData: keepPreviousData,
  });
}

export function usePromoteUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => promoteUser(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.admin.all() });
      toastSuccess('User promoted to admin');
    },
    onError: (e) => toastError(e instanceof ApiError ? e.detail : 'Failed to promote user'),
  });
}

export function useDeleteUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => deleteUser(id),
    onSuccess: () => {
      // Their unfinished lobbies went with them.
      queryClient.invalidateQueries({ queryKey: queryKeys.admin.all() });
      queryClient.invalidateQueries({ queryKey: queryKeys.lobbies.all() });
      toastSuccess('User deleted');
    },
    onError: (e) => toastError(e instanceof ApiError ? e.detail : 'Failed to delete user'),
  });
}

export function useServerStatus() {
  return useQuery({
    queryKey: queryKeys.admin.server(),
    queryFn: getServerStatus,
    refetchInterval: ADMIN_POLL_MS,
  });
}

export function useGameStats() {
  return useQuery({
    queryKey: queryKeys.admin.stats(),
    queryFn: getGameStats,
    refetchInterval: ADMIN_POLL_MS,
  });
}

export function useCategoryStats() {
  return useInfiniteQuery({
    queryKey: queryKeys.admin.categoryStats(),
    queryFn: ({ pageParam }) => getCategoryStats(pageParam, CATEGORY_STATS_PAGE_SIZE),
    initialPageParam: 0,
    getNextPageParam: nextPageParam,
    select: ({ pages }) => flattenPages(pages),
  });
}
