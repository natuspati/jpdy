import { StrictMode, type PropsWithChildren } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { createLobbySocket, type LobbySocket } from '@/sockets/client';
import { useLobbySocket } from './useLobbySocket';

vi.mock('@/sockets/client', () => ({
  createLobbySocket: vi.fn(),
}));

function createSocket(): LobbySocket {
  const socket = {
    connected: false,
    connect: vi.fn(),
    disconnect: vi.fn(),
    on: vi.fn(),
    removeAllListeners: vi.fn(),
  };
  return socket as unknown as LobbySocket;
}

describe('useLobbySocket', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.mocked(createLobbySocket).mockReset();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('does not open the Strict Mode probe socket', () => {
    const probeSocket = createSocket();
    const liveSocket = createSocket();
    vi.mocked(createLobbySocket).mockReturnValueOnce(probeSocket).mockReturnValueOnce(liveSocket);

    const queryClient = new QueryClient();
    const Wrapper = ({ children }: PropsWithChildren) => (
      <StrictMode>
        <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
      </StrictMode>
    );

    const { unmount } = renderHook(() => useLobbySocket({ lobbyId: 7, token: 'test-token' }), {
      wrapper: Wrapper,
    });

    expect(createLobbySocket).toHaveBeenCalledTimes(2);
    expect(probeSocket.disconnect).toHaveBeenCalledOnce();
    expect(probeSocket.connect).not.toHaveBeenCalled();
    expect(liveSocket.connect).not.toHaveBeenCalled();

    act(() => {
      vi.runAllTimers();
    });

    expect(liveSocket.connect).toHaveBeenCalledOnce();

    unmount();
  });

  it('explains a takeover by another tab or device', () => {
    const socket = createSocket();
    vi.mocked(createLobbySocket).mockReturnValueOnce(socket);
    const queryClient = new QueryClient();
    const Wrapper = ({ children }: PropsWithChildren) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
    const { result } = renderHook(() => useLobbySocket({ lobbyId: 7, token: 'test-token' }), {
      wrapper: Wrapper,
    });
    const handler = (name: string) =>
      vi.mocked(socket.on).mock.calls.find(([event]) => event === name)?.[1] as (
        ...args: unknown[]
      ) => void;

    act(() => {
      handler('session_replaced')();
      handler('disconnect')('io server disconnect');
    });

    expect(result.current.status).toBe('closed');
    expect(result.current.reason).toBe('Opened in another tab or device');
  });
});
