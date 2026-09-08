import { describe, expect, it, vi } from 'vitest';

import type { LobbySocket } from './client';
import { emit } from './events';

describe('emit', () => {
  it('preserves the Socket.IO instance when emitting an event without a payload', () => {
    const socket = {
      emit: vi.fn(),
    };
    socket.emit.mockImplementation(function (this: typeof socket, event: string) {
      expect(this).toBe(socket);
      expect(event).toBe('start_game');
    });

    expect(emit(socket as unknown as LobbySocket, 'start_game')).toBe(true);
    expect(socket.emit).toHaveBeenCalledOnce();
  });

  it('attaches a retry-safe command_id to each gameplay command', () => {
    const socket = {
      emit: vi.fn(),
    };

    expect(
      emit(socket as unknown as LobbySocket, 'select_prompt', { prompt_id: 42 }),
    ).toBe(true);
    expect(socket.emit).toHaveBeenCalledWith(
      'select_prompt',
      expect.objectContaining({
        prompt_id: 42,
        command_id: expect.any(String),
      }),
    );
  });
});
