import { useCallback, useEffect, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';

import { queryKeys } from '@/api/queryKeys';
import type { GameLobbyState, HostAnswerKey } from '@/schemas';
import { createLobbySocket, type LobbySocket } from '@/sockets/client';
import { emit as emitEvent } from '@/sockets/events';
import {
  parseHostAnswerKey,
  parseSocketError,
  parseStateChanged,
} from '@/sockets/parseIncoming';
import type { ClientEventName, ClientToServerEvents } from '@/sockets/types';
import { toastError } from '@/store/toastStore';

export type SocketStatus = 'connecting' | 'open' | 'closed' | 'failed';

interface UseLobbySocketArgs {
  lobbyId: number | undefined;
  token: string | null;
}

interface UseLobbySocketResult {
  state: GameLobbyState | null;
  hostAnswerKey: HostAnswerKey | null;
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
  const [hostAnswerKey, setHostAnswerKey] = useState<HostAnswerKey | null>(null);
  const [status, setStatus] = useState<SocketStatus>('connecting');
  const [reason, setReason] = useState<string | null>(null);
  const socketRef = useRef<LobbySocket | null>(null);
  const queryClient = useQueryClient();

  useEffect(() => {
    if (lobbyId === undefined || !token) return;

    const socket = createLobbySocket(lobbyId, token);
    socketRef.current = socket;
    setStatus('connecting');
    setReason(null);
    setState(null);
    setHostAnswerKey(null);

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
      if (parsed.data.phase !== 'player_answering') {
        setHostAnswerKey(null);
      }
      if (
        parsed.data.phase === 'host_selecting_starting_player' ||
        parsed.data.phase === 'player_selecting_prompt' ||
        parsed.data.phase === 'finished'
      ) {
        queryClient.invalidateQueries({ queryKey: queryKeys.lobbies.all() });
      }
    });
    socket.on('host_answer_key', (raw: unknown) => {
      const parsed = parseHostAnswerKey(raw);
      if (!parsed.ok || !parsed.data) {
        toastError('Received invalid host answer key from server');
        return;
      }
      setHostAnswerKey(parsed.data);
    });
    socket.on('error', (raw: unknown) => {
      const parsed = parseSocketError(raw);
      if (parsed.ok && parsed.data) {
        toastError(parsed.data.detail);
      } else {
        toastError('Game error');
      }
    });

    // React Strict Mode deliberately runs effects as setup → cleanup → setup
    // in development. Connecting immediately opens a WebSocket during the
    // first setup only for its cleanup to abort it moments later, which makes
    // Firefox report a spurious failed WebSocket in the console. Deferring
    // the connection one task lets that probe cleanup cancel the first
    // connection while the real mounted effect still connects normally.
    const connectTimer = window.setTimeout(() => {
      socket.connect();
    }, 0);

    return () => {
      window.clearTimeout(connectTimer);
      socket.removeAllListeners();
      socket.disconnect();
      socketRef.current = null;
    };
  }, [lobbyId, queryClient, token]);

  const emit = useCallback<UseLobbySocketResult['emit']>((event, ...args) => {
    const socket = socketRef.current;
    if (!socket || !socket.connected) {
      toastError('Not connected — try again in a moment');
      return false;
    }
    return emitEvent(socket, event, ...args);
  }, []);

  return { state, hostAnswerKey, status, emit, reason };
}
