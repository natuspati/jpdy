import { describe, expect, it } from 'vitest';

import { LobbyRound, LobbyUpdate } from './lobby';
import { PromptCategoryCreate, PromptCategoryInDB } from './prompt';

describe('category setup compatibility', () => {
  const category = { id: 1, name: 'History', owner_id: 2, updated_at: '2026-01-01T00:00:00Z' };

  it('defaults legacy categories to standard and preserves Final kind', () => {
    expect(PromptCategoryInDB.parse(category).kind).toBe('standard');
    expect(PromptCategoryInDB.parse({ ...category, kind: 'final' }).kind).toBe('final');
    expect(PromptCategoryCreate.parse({ name: 'History' }).kind).toBe('standard');
    expect(PromptCategoryCreate.safeParse({ name: 'History', kind: 'other' }).success).toBe(false);
    expect(LobbyRound.parse({ round_number: 1, categories: [category], results: null }).kind).toBe(
      'standard',
    );
    expect(
      LobbyRound.parse({
        round_number: 4,
        kind: 'final',
        categories: [{ ...category, kind: 'final' }],
        results: null,
      }).kind,
    ).toBe('final');
  });

  it('keeps omitted, disabled and selected finals distinct in setup patches', () => {
    expect(LobbyUpdate.parse({ rounds: [[1]] })).not.toHaveProperty('final_category_id');
    expect(LobbyUpdate.parse({ final_category_id: null })).toEqual({ final_category_id: null });
    expect(LobbyUpdate.parse({ rounds: [[1], [2], [3]], final_category_id: 4 })).toEqual({
      rounds: [[1], [2], [3]],
      final_category_id: 4,
    });
    expect(LobbyUpdate.safeParse({ final_category_id: '4' }).success).toBe(false);
  });
});
