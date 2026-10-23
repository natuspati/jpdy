import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { useInfiniteScroll } from './useInfiniteScroll';

describe('useInfiniteScroll', () => {
  let trigger: (isIntersecting: boolean) => void;
  const observe = vi.fn();
  const disconnect = vi.fn();

  beforeEach(() => {
    vi.stubGlobal(
      'IntersectionObserver',
      class {
        constructor(callback: (entries: Array<{ isIntersecting: boolean }>) => void) {
          trigger = (isIntersecting) => callback([{ isIntersecting }]);
        }
        observe = observe;
        disconnect = disconnect;
      },
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    observe.mockClear();
    disconnect.mockClear();
  });

  it('loads more when the sentinel becomes visible, and not while it is off screen', () => {
    const onLoadMore = vi.fn();
    const { result } = renderHook(() => useInfiniteScroll(onLoadMore, true));
    act(() => result.current(document.createElement('div')));

    act(() => trigger(false));
    expect(onLoadMore).not.toHaveBeenCalled();
    act(() => trigger(true));
    expect(onLoadMore).toHaveBeenCalledOnce();
  });

  it('observes nothing while disabled', () => {
    const { result } = renderHook(() => useInfiniteScroll(vi.fn(), false));
    act(() => result.current(document.createElement('div')));
    expect(observe).not.toHaveBeenCalled();
  });
});
