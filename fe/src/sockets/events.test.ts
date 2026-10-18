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

    expect(emit(socket as unknown as LobbySocket, 'select_prompt', { prompt_id: 42 })).toBe(true);
    expect(socket.emit).toHaveBeenCalledWith(
      'select_prompt',
      expect.objectContaining({
        prompt_id: 42,
        command_id: expect.any(String),
      }),
    );
  });

  it('validates every Final payload and attaches command IDs including fenced advance', () => {
    const socket = { emit: vi.fn() };
    const typed = socket as unknown as LobbySocket;
    emit(typed, 'submit_final_wager', { amount: null });
    emit(typed, 'submit_final_answer', { answer: '' });
    emit(typed, 'judge_final_answer', { user_id: 2, correct: false });
    emit(typed, 'advance_final_reveal', { user_id: 2 });
    expect(socket.emit.mock.calls.map((call) => call[0])).toEqual([
      'submit_final_wager',
      'submit_final_answer',
      'judge_final_answer',
      'advance_final_reveal',
    ]);
    for (const [, payload] of socket.emit.mock.calls) {
      expect(payload.command_id).toMatch(/^[a-f0-9-]{36}$/);
    }
    expect(emit(typed, 'submit_final_wager', { amount: 0 })).toBe(false);
    expect(emit(typed, 'submit_final_answer', { answer: 'x'.repeat(257) })).toBe(false);
    expect(socket.emit).toHaveBeenCalledTimes(4);
  });
});
