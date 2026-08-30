import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import {
  createLobby,
  deleteLobby,
  getActiveLobbies,
  getLobby,
  getMyLobbies,
  updateLobby,
} from '@/api/lobbies';
import { ApiError } from '@/api/errors';
import { queryKeys } from '@/api/queryKeys';
import { useAuth } from '@/hooks/useAuth';
import type { LobbyUpdate } from '@/schemas';
import { toastError, toastSuccess } from '@/store/toastStore';

export function useActiveLobbies() {
  const { isAuthed } = useAuth();
  return useQuery({
    queryKey: queryKeys.lobbies.active(),
    queryFn: getActiveLobbies,
    enabled: isAuthed,
    refetchInterval: 10_000,
  });
}

export function useMyLobbies() {
  const { isAuthed } = useAuth();
  return useQuery({
    queryKey: queryKeys.lobbies.mine(),
    queryFn: getMyLobbies,
    enabled: isAuthed,
    refetchInterval: 10_000,
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
    mutationFn: ({ id, payload }: { id: number; payload: LobbyUpdate }) => updateLobby(id, payload),
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
