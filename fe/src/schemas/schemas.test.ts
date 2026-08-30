import { describe, expect, it } from 'vitest';

import { buildGameState } from '@/test/fixtures/gameState';
import {
  GameLobbyState,
  LobbyDetails,
  LobbyInDB,
  PromptInDB,
  TokenResponse,
  UserPublic,
} from './index';

describe('schemas (round-trip)', () => {
  it('UserPublic accepts {id, username}', () => {
    expect(UserPublic.safeParse({ id: 1, username: 'a' }).success).toBe(true);
    expect(UserPublic.safeParse({ id: 'x', username: 'a' }).success).toBe(false);
  });

  it('TokenResponse requires access_token + token_type', () => {
    expect(TokenResponse.safeParse({ access_token: 't', token_type: 'bearer' }).success).toBe(true);
    expect(TokenResponse.safeParse({ access_token: 't' }).success).toBe(false);
  });

  it('LobbyInDB accepts a minimal lobby', () => {
    const ok = LobbyInDB.safeParse({
      id: 1,
      owner_id: 2,
      state: 'created',
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
    });
    expect(ok.success).toBe(true);
  });

  it('LobbyDetails accepts completed rankings', () => {
    expect(
      LobbyDetails.safeParse({
        id: 1,
        owner_id: 2,
        state: 'completed',
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
        owner: { id: 2, username: 'host' },
        prompt_categories: [],
        player_count: 2,
        is_owner: false,
        is_participant: true,
        final_rankings: [
          {
            user_id: 3,
            username: 'player',
            final_score: 500,
            is_banned: false,
            rank: 1,
          },
        ],
      }).success,
    ).toBe(true);
  });

  it('PromptInDB requires question_type enum', () => {
    expect(
      PromptInDB.safeParse({
        id: 1,
        question: 'q',
        question_type: 'banana',
        answer: 'a',
        answer_type: 'text',
        category_id: 1,
        order: 1,
      }).success,
    ).toBe(false);
  });

  it('GameLobbyState round-trip matches the fixture', () => {
    const built = buildGameState();
    const parsed = GameLobbyState.parse(JSON.parse(JSON.stringify(built)));
    expect(parsed).toEqual(built);
  });

  it('rejects an expected answer in a player-visible game state', () => {
    const frame = buildGameState();
    const prompt = frame.categories[0]
      .prompts[0] as (typeof frame.categories)[0]['prompts'][number] & {
      answer: string;
    };
    prompt.answer = 'secret';

    expect(GameLobbyState.safeParse(frame).success).toBe(false);
  });
});
