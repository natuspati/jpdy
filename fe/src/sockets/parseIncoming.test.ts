import { describe, expect, it } from 'vitest';

import { buildGameState } from '@/test/fixtures/gameState';
import {
  parseHostJudgingAnswer,
  parseSocketError,
  parseStateChanged,
} from './parseIncoming';

describe('parseStateChanged', () => {
  it('accepts a valid GameLobbyState', () => {
    const state = buildGameState();
    const result = parseStateChanged(state);
    expect(result.ok).toBe(true);
    expect(result.data?.lobby_id).toBe(state.lobby_id);
  });

  it('rejects an unknown phase', () => {
    const bad = { ...buildGameState(), phase: 'not_a_phase' };
    const result = parseStateChanged(bad);
    expect(result.ok).toBe(false);
  });

  it('rejects when host is missing', () => {
    const bad = { ...buildGameState(), host: undefined };
    const result = parseStateChanged(bad);
    expect(result.ok).toBe(false);
  });

  it('rejects a player frame that leaks an expected answer', () => {
    const state = buildGameState();
    const prompt = state.categories[0].prompts[0] as typeof state.categories[0]['prompts'][number] & {
      answer: string;
    };
    prompt.answer = 'secret';

    expect(parseStateChanged(state).ok).toBe(false);
  });
});

describe('parseHostJudgingAnswer', () => {
  it('accepts host-only expected-answer data', () => {
    const result = parseHostJudgingAnswer({
      lobby_id: 100,
      prompt_id: 101,
      submitted_answer: 'guess',
      expected_answer: 'answer',
    });

    expect(result.ok).toBe(true);
    expect(result.data?.expected_answer).toBe('answer');
  });

  it('rejects unexpected host judging fields', () => {
    expect(
      parseHostJudgingAnswer({
        lobby_id: 100,
        prompt_id: 101,
        submitted_answer: 'guess',
        expected_answer: 'answer',
        unexpected: true,
      }).ok,
    ).toBe(false);
  });
});

describe('parseSocketError', () => {
  it('accepts well-formed error', () => {
    const result = parseSocketError({ code: 'forbidden', detail: 'Nope' });
    expect(result.ok).toBe(true);
    expect(result.data?.code).toBe('forbidden');
  });

  it('rejects missing fields', () => {
    expect(parseSocketError({ code: 'forbidden' }).ok).toBe(false);
    expect(parseSocketError({}).ok).toBe(false);
  });
});
