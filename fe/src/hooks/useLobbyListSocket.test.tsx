import type { PropsWithChildren } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { createLobbyListSocket, type LobbyListSocket } from '@/sockets/client';
import { useLobbyListSocket } from './useLobbyListSocket';

vi.mock('@/sockets/client', () => ({ createLobbyListSocket: vi.fn() }));
vi.mock('@/hooks/useAuth', () => ({ useAuth: () => ({ token: 'test-token' }) }));

describe('useLobbyListSocket', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('refetches the lobby lists on lobbies_changed and after a reconnect, not on first connect', () => {
    const handlers: Record<string, () => void> = {};
    const socket = {
      on: vi.fn((event: string, handler: () => void) => {
        handlers[event] = handler;
      }),
      connect: vi.fn(),
      disconnect: vi.fn(),
      removeAllListeners: vi.fn(),
    };
    vi.mocked(createLobbyListSocket).mockReturnValue(socket as unknown as LobbyListSocket);
    const queryClient = new QueryClient();
    const invalidate = vi.spyOn(queryClient, 'invalidateQueries').mockResolvedValue();
    const wrapper = ({ children }: PropsWithChildren) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );

    const { unmount } = renderHook(() => useLobbyListSocket(), { wrapper });
    act(() => {
      vi.runAllTimers();
    });
    expect(socket.connect).toHaveBeenCalledOnce();

    handlers.connect();
    expect(invalidate).not.toHaveBeenCalled();
    handlers.lobbies_changed();
    expect(invalidate).toHaveBeenCalledTimes(1);
    handlers.connect();
    expect(invalidate).toHaveBeenCalledTimes(2);

    unmount();
    expect(socket.disconnect).toHaveBeenCalledOnce();
  });
});
