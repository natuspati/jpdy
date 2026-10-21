import { useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';

import { queryKeys } from '@/api/queryKeys';
import { useAuth } from '@/hooks/useAuth';
import { createLobbyListSocket } from '@/sockets/client';

/** Refetches the lobby lists whenever the server says they changed (and after a reconnect). */
export function useLobbyListSocket(): void {
  const { token } = useAuth();
  const queryClient = useQueryClient();

  useEffect(() => {
    if (!token) return;

    const socket = createLobbyListSocket(token);
    const refetch = () => void queryClient.invalidateQueries({ queryKey: queryKeys.lobbies.all() });
    let hasConnected = false;
    socket.on('connect', () => {
      // Events sent while disconnected were missed; the first connect already has fresh data.
      if (hasConnected) refetch();
      hasConnected = true;
    });
    socket.on('lobbies_changed', refetch);

    // Deferred so React Strict Mode's setup/cleanup probe never opens a socket.
    const connectTimer = window.setTimeout(() => socket.connect(), 0);

    return () => {
      window.clearTimeout(connectTimer);
      socket.removeAllListeners();
      socket.disconnect();
    };
  }, [queryClient, token]);
}
