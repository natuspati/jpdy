import { StrictMode, type PropsWithChildren } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { createLobbySocket, type LobbySocket } from '@/sockets/client';
import { toastError } from '@/store/toastStore';
import { buildFinalGameState } from '@/test/fixtures/gameState';
import { useLobbySocket } from './useLobbySocket';

vi.mock('@/sockets/client', () => ({
  createLobbySocket: vi.fn(),
}));

vi.mock('@/store/toastStore', () => ({ toastError: vi.fn() }));

function createSocket(): LobbySocket {
  const socket = {
    connected: false,
    connect: vi.fn(),
    disconnect: vi.fn(),
    on: vi.fn(),
    removeAllListeners: vi.fn(),
    emit: vi.fn(),
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

  it('keeps Final commands pending until own acceptance, permits retry after errors, and restores reconnect state', () => {
    const socket = createSocket();
    Object.assign(socket, { connected: true });
    vi.mocked(createLobbySocket).mockReturnValue(socket);
    const queryClient = new QueryClient();
    const Wrapper = ({ children }: PropsWithChildren) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
    const { result } = renderHook(
      () => useLobbySocket({ lobbyId: 100, token: 'token', userId: 2 }),
      { wrapper: Wrapper },
    );
    const handler = (name: string) =>
      vi.mocked(socket.on).mock.calls.find(([event]) => event === name)?.[1] as (
        ...args: unknown[]
      ) => void;
    const state = buildFinalGameState();
    act(() => handler('state_changed')(state));
    act(() => {
      result.current.emit('submit_final_wager', { amount: 200 });
    });
    expect(result.current.pendingCommand).toBe('submit_final_wager');
    act(() => {
      expect(result.current.emit('submit_final_wager', { amount: null })).toBe(false);
    });
    state.state_revision++;
    state.final_round!.players[1].decision_submitted = true;
    act(() => handler('state_changed')(state));
    expect(result.current.pendingCommand).toBe('submit_final_wager');
    state.state_revision++;
    Object.assign(state.final_round!.players[0], { decision_submitted: true, wager: 200 });
    act(() => handler('state_changed')(state));
    expect(result.current.pendingCommand).toBeNull();

    const answering = buildFinalGameState('final_answering');
    answering.state_revision = 3;
    act(() => handler('state_changed')(answering));
    act(() => {
      result.current.emit('submit_final_answer', { answer: 'Draft' });
    });
    act(() => handler('error')({ code: 'retry', detail: 'Submission failed' }));
    expect(result.current.pendingCommand).toBeNull();
    expect(result.current.commandError).toBe('Submission failed');
    act(() => {
      result.current.emit('submit_final_answer', { answer: 'Retry' });
    });
    expect(result.current.commandError).toBeNull();
    act(() => handler('disconnect')('transport close'));
    expect(result.current.pendingCommand).toBeNull();
    Object.assign(answering.final_round!.players[0], { answer_submitted: true, answer: 'Retry' });
    answering.state_revision++;
    act(() => {
      handler('connect')();
      handler('state_changed')(answering);
    });
    expect(result.current.state?.final_round?.players[0].answer).toBe('Retry');
    expect(result.current.state?.timer_deadline).toBe(answering.timer_deadline);
  });

  it('keeps retrying quietly on transport errors and fails only on server rejection', () => {
    const socket = createSocket();
    const handlers = new Map<string, (...args: unknown[]) => void>();
    vi.mocked(socket.on).mockImplementation(((event: string, handler: never) => {
      handlers.set(event, handler);
      return socket;
    }) as never);
    vi.mocked(createLobbySocket).mockReturnValue(socket);
    vi.mocked(toastError).mockClear();

    const queryClient = new QueryClient();
    const Wrapper = ({ children }: PropsWithChildren) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
    const { result } = renderHook(() => useLobbySocket({ lobbyId: 7, token: 'test-token' }), {
      wrapper: Wrapper,
    });

    Object.assign(socket, { active: true });
    act(() => handlers.get('connect_error')?.(new Error('websocket error')));
    expect(result.current.status).toBe('connecting');
    expect(result.current.reason).toBe('websocket error');
    expect(toastError).not.toHaveBeenCalled();

    Object.assign(socket, { active: false });
    act(() => handlers.get('connect_error')?.(new Error('Player is banned from this lobby')));
    expect(result.current.status).toBe('failed');
    expect(toastError).toHaveBeenCalledWith('Player is banned from this lobby');
  });

  it('clears a pending fenced host judgment when a ban advances to another response', () => {
    const socket = createSocket();
    Object.assign(socket, { connected: true });
    vi.mocked(createLobbySocket).mockReturnValue(socket);
    const queryClient = new QueryClient();
    const Wrapper = ({ children }: PropsWithChildren) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
    const { result } = renderHook(
      () => useLobbySocket({ lobbyId: 100, token: 'token', userId: 1 }),
      { wrapper: Wrapper },
    );
    const onState = vi
      .mocked(socket.on)
      .mock.calls.find(([event]) => event === 'state_changed')?.[1] as (frame: unknown) => void;
    const state = buildFinalGameState('final_reveal');
    act(() => onState(state));
    act(() => {
      result.current.emit('judge_final_answer', { user_id: 2, correct: true });
    });
    expect(result.current.pendingCommand).toBe('judge_final_answer');
    Object.assign(state.final_round!.players[0], { removed: true, wager: null, answer: null });
    Object.assign(state.final_round!.players[1], { revealed: true, answer: 'Next response' });
    state.final_round!.current_user_id = 3;
    state.state_revision++;
    act(() => onState(state));
    expect(result.current.pendingCommand).toBeNull();
  });
});
