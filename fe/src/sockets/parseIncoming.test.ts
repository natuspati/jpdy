import { describe, expect, it } from 'vitest';

import { buildGameState } from '@/test/fixtures/gameState';
import { parseSocketError, parseStateChanged } from './parseIncoming';

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
