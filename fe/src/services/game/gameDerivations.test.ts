import { describe, expect, it } from 'vitest';

import { buildGameState } from '@/test/fixtures/gameState';
import { sortedScoreboard } from './gameDerivations';

describe('sortedScoreboard', () => {
  it('sorts active players by score, username, then user id', () => {
    const state = buildGameState({
      players: [
        { user_id: 4, username: 'zoe', score: 500 },
        { user_id: 3, username: 'alice', score: 500 },
        { user_id: 2, username: 'alice', score: 500 },
        { user_id: 5, username: 'bob', score: 300 },
      ],
    });

    expect(sortedScoreboard(state).map((player) => player.user_id)).toEqual([2, 3, 4, 5]);
  });

  it('keeps banned players after every active player', () => {
    const state = buildGameState({
      players: [
        { user_id: 2, username: 'banned', score: 1_000, is_banned: true },
        { user_id: 3, username: 'active', score: 100 },
        { user_id: 4, username: 'also-banned', score: 500, is_banned: true },
      ],
    });

    expect(sortedScoreboard(state).map((player) => player.user_id)).toEqual([3, 2, 4]);
  });
});
