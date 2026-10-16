import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { buildGameState } from '@/test/fixtures/gameState';
import { SELECTION_REVEAL_MS, useSelectionReveal } from './useSelectionReveal';

const selecting = buildGameState({ phase: 'player_selecting_prompt', selectingPlayerId: 2 });
const answering = { ...selecting, phase: 'player_answering' as const, current_prompt_id: 101 };

describe('useSelectionReveal', () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it('holds the picked prompt for a second, then releases it', () => {
    const { result, rerender } = renderHook(({ state }) => useSelectionReveal(state), {
      initialProps: { state: selecting },
    });
    expect(result.current).toBeNull();

    rerender({ state: answering });
    expect(result.current).toBe(101);

    act(() => {
      vi.advanceTimersByTime(SELECTION_REVEAL_MS);
    });
    expect(result.current).toBeNull();
  });

  it('also holds the picked prompt when it opens betting', () => {
    const betting = { ...selecting, phase: 'player_betting' as const, current_prompt_id: 101 };
    const { result, rerender } = renderHook(({ state }) => useSelectionReveal(state), {
      initialProps: { state: selecting },
    });

    rerender({ state: betting });
    expect(result.current).toBe(101);

    act(() => {
      vi.advanceTimersByTime(SELECTION_REVEAL_MS);
    });
    expect(result.current).toBeNull();
  });

  it('does not pause when joining a clue that is already open', () => {
    const { result } = renderHook(() => useSelectionReveal(answering));
    expect(result.current).toBeNull();
  });
});
