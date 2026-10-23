import { describe, expect, it } from 'vitest';

import { flattenPages, nextPageParam } from './pagination';

describe('pagination helpers', () => {
  it('asks for the next page only while rows remain', () => {
    expect(nextPageParam({ page: 0, size: 10, total: 11 })).toBe(1);
    expect(nextPageParam({ page: 1, size: 10, total: 20 })).toBeUndefined();
    expect(nextPageParam({ page: 0, size: 10, total: 0 })).toBeUndefined();
  });

  it('flattens pages and keeps one row per id', () => {
    const pages = [{ contents: [{ id: 1 }, { id: 2 }] }, { contents: [{ id: 2 }, { id: 3 }] }];
    expect(flattenPages(pages).map((item) => item.id)).toEqual([1, 2, 3]);
  });
});
