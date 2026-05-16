import { describe, expect, it } from 'vitest';

import { buildGameState } from '@/test/fixtures/gameState';
import { roleFor } from './roleFor';

describe('roleFor', () => {
  it('returns host for the lobby owner regardless of phase', () => {
    const state = buildGameState({ phase: 'player_selecting_prompt' });
    expect(roleFor(state, 1)).toBe('host');
  });

  it('returns banned for a banned player', () => {
    const state = buildGameState({
      players: [{ user_id: 2, username: 'alice', is_banned: true }],
    });
    expect(roleFor(state, 2)).toBe('banned');
  });

  it('returns answerer when answering_player_id matches', () => {
    const state = buildGameState({
      phase: 'player_answering',
      answeringPlayerId: 2,
    });
    expect(roleFor(state, 2)).toBe('answerer');
  });

  it('returns selector when player is the picker in selecting phase', () => {
    const state = buildGameState({
      phase: 'player_selecting_prompt',
      selectingPlayerId: 2,
    });
    expect(roleFor(state, 2)).toBe('selector');
  });

  it('returns buzzer for eligible player during buzz_open', () => {
    const state = buildGameState({
      phase: 'buzz_open',
      attemptedPlayerIds: [3],
    });
    expect(roleFor(state, 2)).toBe('buzzer');
  });

  it('returns spectator when buzz_open but already attempted', () => {
    const state = buildGameState({
      phase: 'buzz_open',
      attemptedPlayerIds: [2],
    });
    expect(roleFor(state, 2)).toBe('spectator');
  });

  it('returns spectator for player when waiting', () => {
    const state = buildGameState();
    expect(roleFor(state, 2)).toBe('spectator');
  });
});
