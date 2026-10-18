import { useCallback, useEffect, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';

import { queryKeys } from '@/api/queryKeys';
import type { GameLobbyState, GameSoundCuePayload, HostAnswerKey } from '@/schemas';
import { createLobbySocket, type LobbySocket } from '@/sockets/client';
import { emit as emitEvent } from '@/sockets/events';
import {
  parseHostAnswerKey,
  parseGameSoundCue,
  parseLobbyDeleted,
  parseSocketError,
  parseStateChanged,
} from '@/sockets/parseIncoming';
import type { ClientEventName, ClientToServerEvents } from '@/sockets/types';
import { toastError } from '@/store/toastStore';

export type SocketStatus = 'connecting' | 'open' | 'closed' | 'failed';

interface UseLobbySocketArgs {
  lobbyId: number | undefined;
  token: string | null;
  userId?: number | null;
}

interface UseLobbySocketResult {
  state: GameLobbyState | null;
  hostAnswerKey: HostAnswerKey | null;
  soundCue: GameSoundCuePayload | null;
  lobbyDeleted: boolean;
  status: SocketStatus;
  emit: <E extends ClientEventName>(
    event: E,
    ...args: Parameters<ClientToServerEvents[E]>
  ) => boolean;
  reconnect: () => void;
  reason: string | null;
  pendingCommand: ClientEventName | null;
  commandError: string | null;
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
  userId,
}: UseLobbySocketArgs): UseLobbySocketResult {
  const [state, setState] = useState<GameLobbyState | null>(null);
  const [hostAnswerKey, setHostAnswerKey] = useState<HostAnswerKey | null>(null);
  const [soundCue, setSoundCue] = useState<GameSoundCuePayload | null>(null);
  const [lobbyDeleted, setLobbyDeleted] = useState(false);
  const [status, setStatus] = useState<SocketStatus>('connecting');
  const [reason, setReason] = useState<string | null>(null);
  const [pendingCommand, setPendingCommand] = useState<ClientEventName | null>(null);
  const [commandError, setCommandError] = useState<string | null>(null);
  const pendingRef = useRef<{ event: ClientEventName; targetId?: number } | null>(null);
  const socketRef = useRef<LobbySocket | null>(null);
  const lobbyDeletedRef = useRef(false);
  const sessionReplacedRef = useRef(false);
  const latestCueIdRef = useRef(0);
  const latestStateRevisionRef = useRef(-1);
  const queryClient = useQueryClient();

  useEffect(() => {
    if (lobbyId === undefined || !token) return;

    const socket = createLobbySocket(lobbyId, token);
    socketRef.current = socket;
    setStatus('connecting');
    setReason(null);
    setState(null);
    setHostAnswerKey(null);
    setSoundCue(null);
    setLobbyDeleted(false);
    setPendingCommand(null);
    setCommandError(null);
    pendingRef.current = null;
    lobbyDeletedRef.current = false;
    sessionReplacedRef.current = false;
    latestCueIdRef.current = 0;
    latestStateRevisionRef.current = -1;

    socket.on('connect', () => {
      sessionReplacedRef.current = false;
      setStatus('open');
      setReason(null);
    });
    socket.on('disconnect', (r) => {
      pendingRef.current = null;
      setPendingCommand(null);
      if (lobbyDeletedRef.current) return;
      if (sessionReplacedRef.current) {
        setStatus('closed');
        setReason('Opened in another tab or device');
        return;
      }
      if (r !== 'io server disconnect' && r !== 'io client disconnect') {
        setStatus('connecting');
        setReason('Connection lost. Reconnecting…');
        return;
      }
      setStatus('closed');
      if (typeof r === 'string') setReason(r);
    });
    socket.on('connect_error', (err) => {
      const message = err instanceof Error ? err.message : 'Socket connection failed';
      setReason(message);
      // Transport errors (network or proxy blips) are retried by the client: keep the game on
      // screen with a reconnecting banner. Only a server rejection ends the retries.
      if (socket.active) {
        setStatus('connecting');
        return;
      }
      setStatus('failed');
      toastError(message);
    });
    socket.on('state_changed', (raw: unknown) => {
      const parsed = parseStateChanged(raw);
      if (!parsed.ok || !parsed.data) {
        toastError('Received invalid game state from server');
        return;
      }
      if (parsed.data.state_revision < latestStateRevisionRef.current) return;
      latestStateRevisionRef.current = parsed.data.state_revision;
      setState(parsed.data);
      const pending = pendingRef.current;
      const final = parsed.data.final_round;
      const own = final?.players.find((player) => player.user_id === userId);
      if (
        pending &&
        ((pending.event === 'submit_final_wager' &&
          (parsed.data.phase !== 'final_betting' ||
            !own ||
            own.decision_submitted ||
            own.removed)) ||
          (pending.event === 'submit_final_answer' &&
            (parsed.data.phase !== 'final_answering' ||
              !own ||
              own.answer_submitted ||
              own.removed)) ||
          (pending.event === 'judge_final_answer' &&
            (parsed.data.phase !== 'final_reveal' ||
              final?.current_user_id !== pending.targetId ||
              final?.players.find((player) => player.user_id === pending.targetId)?.correct !=
                null)) ||
          (pending.event === 'advance_final_reveal' &&
            (parsed.data.phase !== 'final_reveal' || final?.current_user_id !== pending.targetId)))
      ) {
        pendingRef.current = null;
        setPendingCommand(null);
      }
      latestCueIdRef.current = Math.max(
        latestCueIdRef.current,
        parsed.data.latest_sound_cue_id ?? 0,
      );
      if (parsed.data.phase !== 'player_answering') {
        setHostAnswerKey(null);
      }
      queryClient.invalidateQueries({ queryKey: queryKeys.lobbies.all() });
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
      if (pendingRef.current) {
        setCommandError(parsed.ok && parsed.data ? parsed.data.detail : 'Game error');
        pendingRef.current = null;
        setPendingCommand(null);
      }
      if (parsed.ok && parsed.data) {
        toastError(parsed.data.detail);
      } else {
        toastError('Game error');
      }
    });
    socket.on('game_sound_cue', (raw: unknown) => {
      const parsed = parseGameSoundCue(raw);
      if (!parsed.ok || !parsed.data) return;
      if (parsed.data.cue_id <= latestCueIdRef.current) return;
      latestCueIdRef.current = parsed.data.cue_id;
      setSoundCue(parsed.data);
    });
    socket.on('session_replaced', () => {
      sessionReplacedRef.current = true;
    });
    socket.on('lobby_deleted', (raw: unknown) => {
      const parsed = parseLobbyDeleted(raw);
      if (!parsed.ok || !parsed.data || parsed.data.lobby_id !== lobbyId) return;
      lobbyDeletedRef.current = true;
      setLobbyDeleted(true);
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
  }, [lobbyId, queryClient, token, userId]);

  const emit = useCallback<UseLobbySocketResult['emit']>((event, ...args) => {
    const socket = socketRef.current;
    if (!socket || !socket.connected) {
      toastError('Not connected — try again in a moment');
      return false;
    }
    const isFinalCommand =
      event === 'submit_final_wager' ||
      event === 'submit_final_answer' ||
      event === 'judge_final_answer' ||
      event === 'advance_final_reveal';
    if (isFinalCommand && pendingRef.current) return false;
    const sent = emitEvent(socket, event, ...args);
    if (sent && isFinalCommand) {
      const payload = args[0];
      pendingRef.current = {
        event,
        targetId: payload && 'user_id' in payload ? payload.user_id : undefined,
      };
      setPendingCommand(event);
      setCommandError(null);
    }
    return sent;
  }, []);

  const reconnect = useCallback(() => {
    const socket = socketRef.current;
    if (!socket || socket.connected || lobbyDeletedRef.current) return;
    setStatus('connecting');
    setReason(null);
    socket.connect();
  }, []);

  return {
    state,
    hostAnswerKey,
    soundCue,
    lobbyDeleted,
    status,
    emit,
    reconnect,
    reason,
    pendingCommand,
    commandError,
  };
}
