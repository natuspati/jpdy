import { io, type Socket } from 'socket.io-client';

import { env } from '@/config/env';
import type { ClientToServerEvents, ServerToClientEvents } from './types';

export type LobbySocket = Socket<ServerToClientEvents, ClientToServerEvents>;

export function createLobbySocket(lobbyId: number, token: string): LobbySocket {
  return io(`${env.SOCKET_URL}/lobbies/${lobbyId}`, {
    path: env.SOCKET_PATH,
    // WebSocket-only: no HTTP long-polling, so multiple backend replicas need no sticky sessions.
    transports: ['websocket'],
    query: { token },
    autoConnect: false,
    reconnection: true,
    reconnectionAttempts: Infinity,
    reconnectionDelay: 500,
    reconnectionDelayMax: 2_000,
  });
}
