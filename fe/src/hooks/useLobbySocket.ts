import { useCallback, useEffect, useRef, useState } from 'react';

import type { GameLobbyState } from '@/schemas';
import { createLobbySocket, type LobbySocket } from '@/sockets/client';
import { emit as emitEvent } from '@/sockets/events';
import { parseSocketError, parseStateChanged } from '@/sockets/parseIncoming';
import type { ClientEventName, ClientToServerEvents } from '@/sockets/types';
import { toastError } from '@/store/toastStore';

export type SocketStatus = 'connecting' | 'open' | 'closed' | 'failed';

interface UseLobbySocketArgs {
  lobbyId: number | undefined;
  token: string | null;
}

interface UseLobbySocketResult {
  state: GameLobbyState | null;
  status: SocketStatus;
  emit: <E extends ClientEventName>(
    event: E,
    ...args: Parameters<ClientToServerEvents[E]>
  ) => boolean;
  reason: string | null;
}

/**
 * Owns the socket lifecycle for a single lobby namespace.
 *
 * - Builds the socket on mount, connects, and tears it down on unmount or
 *   when lobbyId/token change.
 * - Stores latest validated `GameLobbyState` snapshot; bad frames are
 *   dropped + toasted (per plan §3).
 * - Surfaces a `status` for the page to render connecting/failed banners.
 */
export function useLobbySocket({
  lobbyId,
  token,
}: UseLobbySocketArgs): UseLobbySocketResult {
  const [state, setState] = useState<GameLobbyState | null>(null);
  const [status, setStatus] = useState<SocketStatus>('connecting');
  const [reason, setReason] = useState<string | null>(null);
  const socketRef = useRef<LobbySocket | null>(null);

  useEffect(() => {
    if (lobbyId === undefined || !token) return;

    const socket = createLobbySocket(lobbyId, token);
    socketRef.current = socket;
    setStatus('connecting');
    setReason(null);

    socket.on('connect', () => setStatus('open'));
    socket.on('disconnect', (r) => {
      setStatus('closed');
      if (typeof r === 'string') setReason(r);
    });
    socket.on('connect_error', (err) => {
      setStatus('failed');
      const message = err instanceof Error ? err.message : 'Socket connection failed';
      setReason(message);
      toastError(message);
    });
    socket.on('state_changed', (raw: unknown) => {
      const parsed = parseStateChanged(raw);
      if (!parsed.ok || !parsed.data) {
        toastError('Received invalid game state from server');
        return;
      }
      setState(parsed.data);
    });
    socket.on('error', (raw: unknown) => {
      const parsed = parseSocketError(raw);
      if (parsed.ok && parsed.data) {
        toastError(parsed.data.detail);
      } else {
        toastError('Game error');
      }
    });

    socket.connect();

    return () => {
      socket.removeAllListeners();
      socket.disconnect();
      socketRef.current = null;
    };
  }, [lobbyId, token]);

  const emit = useCallback<UseLobbySocketResult['emit']>((event, ...args) => {
    const socket = socketRef.current;
    if (!socket || !socket.connected) {
      toastError('Not connected — try again in a moment');
      return false;
    }
    return emitEvent(socket, event, ...args);
  }, []);

  return { state, status, emit, reason };
}
