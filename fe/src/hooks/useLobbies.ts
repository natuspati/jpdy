import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { createLobby, deleteLobby, getLobby, searchLobbies, updateLobby } from '@/api/lobbies';
import { ApiError } from '@/api/errors';
import { queryKeys } from '@/api/queryKeys';
import { useAuth } from '@/hooks/useAuth';
import type { LobbyFilter, LobbyUpdate } from '@/schemas';
import { toastError, toastSuccess } from '@/store/toastStore';

export function useJoinableLobbies(filters: Partial<LobbyFilter> = {}) {
  const { isAuthed } = useAuth();
  const merged: Partial<LobbyFilter> = { states: ['waiting_start'], size: 50, ...filters };
  return useQuery({
    queryKey: queryKeys.lobbies.list(merged),
    queryFn: () => searchLobbies(merged),
    enabled: isAuthed,
    refetchInterval: 10_000,
  });
}

export function useMyLobbies() {
  const { userId, isAuthed } = useAuth();
  const filters: Partial<LobbyFilter> = userId ? { owner_ids: [userId], size: 50 } : {};
  return useQuery({
    queryKey: queryKeys.lobbies.list({ ...filters, scope: 'mine' } as Partial<LobbyFilter>),
    queryFn: () => searchLobbies(filters),
    enabled: isAuthed && userId !== null,
  });
}

export function useLobby(id: number | undefined) {
  return useQuery({
    queryKey: id ? queryKeys.lobbies.detail(id) : ['lobbies', 'detail', 'none'],
    queryFn: () => getLobby(id as number),
    enabled: id !== undefined,
  });
}

export function useCreateLobby() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => createLobby(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.lobbies.all() });
    },
    onError: (e) => toastError(e instanceof ApiError ? e.detail : 'Failed to create lobby'),
  });
}

export function useUpdateLobby() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: LobbyUpdate }) =>
      updateLobby(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.lobbies.all() });
    },
    onError: (e) => toastError(e instanceof ApiError ? e.detail : 'Failed to update lobby'),
  });
}

export function useDeleteLobby() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => deleteLobby(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.lobbies.all() });
      toastSuccess('Lobby deleted');
    },
    onError: (e) => toastError(e instanceof ApiError ? e.detail : 'Failed to delete lobby'),
  });
}
