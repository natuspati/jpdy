import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { useCountdown } from './useCountdown';

describe('useCountdown', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-01-01T00:00:00Z'));
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it('returns null when deadline is null', () => {
    const { result } = renderHook(() => useCountdown(null));
    expect(result.current).toBeNull();
  });

  it('counts down toward 0', () => {
    const deadline = new Date('2026-01-01T00:00:10Z').toISOString();
    const { result } = renderHook(() => useCountdown(deadline));
    expect(result.current).toBe(10);
    act(() => {
      vi.advanceTimersByTime(5_000);
    });
    expect(result.current).toBe(5);
    act(() => {
      vi.advanceTimersByTime(10_000);
    });
    expect(result.current).toBe(0);
  });

  it('reacts to a new deadline', () => {
    const first = new Date('2026-01-01T00:00:05Z').toISOString();
    const { result, rerender } = renderHook(({ d }) => useCountdown(d), {
      initialProps: { d: first },
    });
    expect(result.current).toBe(5);
    const longer = new Date('2026-01-01T00:00:30Z').toISOString();
    rerender({ d: longer });
    expect(result.current).toBe(30);
  });
});
