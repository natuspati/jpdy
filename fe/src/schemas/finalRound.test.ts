import { describe, expect, it } from 'vitest';

import { buildFinalGameState, buildGameState } from '@/test/fixtures/gameState';
import { type GameCategoryState, GameLobbyState } from './game';
import { SubmitFinalAnswerPayload, SubmitFinalWagerPayload } from './socketEvents';

describe('Final public snapshot contract', () => {
  it('keeps legacy defaults and accepts each valid Final phase', () => {
    const legacy = buildGameState() as Partial<ReturnType<typeof buildGameState>>;
    delete legacy.final_round;
    const category = legacy.categories![0] as Partial<GameCategoryState>;
    delete category.kind;
    const parsed = GameLobbyState.parse(legacy);
    expect(parsed.final_round).toBeNull();
    expect(parsed.categories[0].kind).toBe('standard');
    for (const phase of ['final_betting', 'final_answering', 'final_reveal'] as const) {
      expect(GameLobbyState.safeParse(buildFinalGameState(phase)).success).toBe(true);
    }
  });

  it('rejects premature Final question text, media, canonical content and reveal metadata', () => {
    const media = { asset_id: 1, url: '/secret', mime_type: 'image/png', filename: 'secret' };
    for (const change of [
      (s: ReturnType<typeof buildFinalGameState>) => {
        s.categories[1].prompts[0].question = 'Secret';
      },
      (s: ReturnType<typeof buildFinalGameState>) => {
        s.categories[1].prompts[0].question_media = media;
      },
      (s: ReturnType<typeof buildFinalGameState>) => {
        s.categories[1].prompts[0].answer_media = media;
      },
      (s: ReturnType<typeof buildFinalGameState>) => {
        s.final_round!.correct_answer = 'Secret';
      },
      (s: ReturnType<typeof buildFinalGameState>) => {
        s.final_round!.correct_answer_media = media;
      },
      (s: ReturnType<typeof buildFinalGameState>) => {
        s.final_round!.players[0].revealed = true;
      },
      (s: ReturnType<typeof buildFinalGameState>) => {
        s.final_round!.current_user_id = 2;
      },
    ]) {
      const state = buildFinalGameState();
      change(state);
      expect(GameLobbyState.safeParse(state).success).toBe(false);
    }
    const answering = buildFinalGameState('final_answering');
    answering.final_round!.correct_answer = 'Too early';
    expect(GameLobbyState.safeParse(answering).success).toBe(false);
  });

  it('rejects incomplete or inconsistent judgments and normal resolution leakage', () => {
    const state = buildFinalGameState('final_reveal');
    const player = state.final_round!.players[0];
    player.correct = true;
    expect(GameLobbyState.safeParse(state).success).toBe(false);
    Object.assign(player, { score_delta: 200, updated_score: 700 });
    expect(GameLobbyState.safeParse(state).success).toBe(true);
    player.revealed = false;
    expect(GameLobbyState.safeParse(state).success).toBe(false);
    player.revealed = true;
    state.resolved_answer_type = 'text';
    expect(GameLobbyState.safeParse(state).success).toBe(false);
  });

  it('requires Final state, a revealed fenced player, and scoreless non-auction prompts', () => {
    const state = buildFinalGameState('final_reveal');
    state.final_round!.current_user_id = 999;
    expect(GameLobbyState.safeParse(state).success).toBe(false);
    state.final_round!.current_user_id = 2;
    state.categories[1].prompts[0].score_value = 100;
    expect(GameLobbyState.safeParse(state).success).toBe(false);
    state.categories[1].prompts[0].score_value = null;
    state.categories[1].prompts[0].is_betting = true;
    expect(GameLobbyState.safeParse(state).success).toBe(false);
    state.final_round = null;
    expect(GameLobbyState.safeParse(state).success).toBe(false);
  });

  it('accepts removed unjudged reveals and canonical completion after revealed rows are banned', () => {
    const state = buildFinalGameState('final_reveal');
    Object.assign(state.final_round!.players[0], {
      removed: true,
      answer: null,
      wager: null,
    });
    Object.assign(state.final_round!.players[1], {
      revealed: true,
      answer: 'Second response',
    });
    state.final_round!.current_user_id = 3;
    expect(GameLobbyState.safeParse(state).success).toBe(true);
    state.phase = 'finished';
    state.final_round!.current_user_id = null;
    state.final_round!.players = [state.final_round!.players[0]];
    state.final_round!.players[0].revealed = false;
    expect(GameLobbyState.safeParse(state).success).toBe(true);
    state.final_round!.skipped_reason = 'all_passed';
    expect(GameLobbyState.safeParse(state).success).toBe(false);
  });

  it('accepts own private submissions but rejects invalid wager and answer payloads', () => {
    const state = buildFinalGameState();
    Object.assign(state.final_round!.players[0], { wager: 100, decision_submitted: true });
    expect(GameLobbyState.safeParse(state).success).toBe(true);
    for (const amount of [-1, 0.5, true, '10', undefined]) {
      expect(SubmitFinalWagerPayload.safeParse({ amount }).success).toBe(false);
    }
    expect(SubmitFinalWagerPayload.safeParse({ amount: null }).success).toBe(true);
    expect(SubmitFinalWagerPayload.safeParse({ amount: 0 }).success).toBe(true);
    expect(SubmitFinalAnswerPayload.safeParse({ answer: '' }).success).toBe(true);
    expect(SubmitFinalAnswerPayload.safeParse({ answer: 'x'.repeat(257) }).success).toBe(false);
  });
});
