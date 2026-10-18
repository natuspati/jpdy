import { renderHook, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { GameCategoryState, GamePhaseEnum, MediaReference } from '@/schemas';

import { preloadedSrc, useBoardMediaPreload } from './useBoardMediaPreload';

const media = (url: string, mime_type = 'video/mp4'): MediaReference => ({
  asset_id: 1,
  url,
  mime_type,
  filename: 'clue',
});

const categories = (
  ...items: [MediaReference | null, (MediaReference | null)?][]
): GameCategoryState[] => [
  {
    category_id: 1,
    name: 'Category',
    kind: 'standard',
    round_number: 1,
    prompts: items.map(([question_media, answer_media], index) => ({
      prompt_id: index + 1,
      question: '',
      question_media,
      answer_media: answer_media ?? null,
      order: index + 1,
      is_selected: false,
      score_value: (index + 1) * 100,
      is_betting: false,
    })),
  },
];

describe('useBoardMediaPreload', () => {
  const fetched: string[] = [];

  beforeEach(() => {
    fetched.length = 0;
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string) => {
        fetched.push(url);
        if (url === '/media/broken.mp4') return new Response('nope', { status: 500 });
        return new Response(new Blob(['x']));
      }),
    );
    URL.createObjectURL = vi.fn((blob: Blob) => `blob:${blob.size}`);
    URL.revokeObjectURL = vi.fn();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('fetches question and answer media once each and exposes local blob URLs', async () => {
    const board = categories(
      [media('/media/a.mp4'), media('/media/a-answer.png', 'image/png')],
      [media('/media/a.mp4')],
      [null],
    );

    const { result, rerender } = renderHook(({ value }) => useBoardMediaPreload(value), {
      initialProps: { value: board },
    });
    expect(result.current.total).toBe(2);
    await waitFor(() => expect(result.current.loaded).toBe(2));
    rerender({ value: [...board] });

    expect([...fetched].sort()).toEqual(['/media/a-answer.png', '/media/a.mp4']);
    expect(preloadedSrc(media('/media/a.mp4'))).toBe('blob:1');
    expect(preloadedSrc(media('/media/other.mp4'))).toBeNull();
  });

  it('counts failed fetches as loaded so the game cannot deadlock', async () => {
    const { result } = renderHook(() =>
      useBoardMediaPreload(categories([media('/media/broken.mp4')])),
    );

    await waitFor(() => expect(result.current).toEqual({ loaded: 1, total: 1 }));
    expect(preloadedSrc(media('/media/broken.mp4'))).toBeNull();
  });

  it('is immediately complete when the board has no media', () => {
    const { result } = renderHook(() => useBoardMediaPreload(categories([null])));

    expect(result.current).toEqual({ loaded: 0, total: 0 });
  });

  it('preloads media from every round, not only the current one', async () => {
    const [roundOne] = categories([media('/media/r1.mp4')]);
    const [roundTwoBase] = categories([media('/media/r2.mp4')]);
    const roundTwo = { ...roundTwoBase, category_id: 2, round_number: 2 };

    const { result } = renderHook(() => useBoardMediaPreload([roundOne, roundTwo]));

    await waitFor(() => expect(result.current).toEqual({ loaded: 2, total: 2 }));
    expect([...fetched].sort()).toEqual(['/media/r1.mp4', '/media/r2.mp4']);
  });

  it('never preloads Final media before its phase, then loads question and canonical separately', async () => {
    const board = categories([media('/final-question'), media('/final-answer')]);
    board[0].kind = 'final';
    const { result, rerender } = renderHook(
      ({ phase }: { phase: GamePhaseEnum }) => useBoardMediaPreload(board, phase),
      { initialProps: { phase: 'final_betting' as GamePhaseEnum } },
    );
    expect(result.current.total).toBe(0);
    expect(fetched).toEqual([]);
    rerender({ phase: 'final_answering' });
    await waitFor(() => expect(result.current.loaded).toBe(1));
    expect(fetched).toEqual(['/final-question']);
    rerender({ phase: 'final_reveal' });
    await waitFor(() => expect(result.current.loaded).toBe(2));
    expect(fetched).toEqual(['/final-question', '/final-answer']);
  });
});
