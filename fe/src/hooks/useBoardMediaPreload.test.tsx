import { renderHook } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { GameCategoryState, MediaReference } from '@/schemas';

import { useBoardMediaPreload } from './useBoardMediaPreload';

const media = (url: string, mime_type: string): MediaReference => ({
  asset_id: 1,
  url,
  mime_type,
  filename: 'clue',
});

const categories = (...items: (MediaReference | null)[]): GameCategoryState[] => [
  {
    category_id: 1,
    name: 'Category',
    prompts: items.map((question_media, index) => ({
      prompt_id: index + 1,
      question: '',
      question_media,
      order: index + 1,
      is_selected: false,
      score_value: (index + 1) * 100,
    })),
  },
];

describe('useBoardMediaPreload', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('preloads each board image once and skips non-image media', () => {
    const loaded: string[] = [];
    vi.stubGlobal(
      'Image',
      class {
        decoding = '';
        set src(value: string) {
          loaded.push(value);
        }
      },
    );
    const board = categories(
      media('/media/a.webp', 'image/webp'),
      media('/media/b.mp4', 'video/mp4'),
      null,
    );

    const { rerender } = renderHook(({ value }) => useBoardMediaPreload(value), {
      initialProps: { value: board },
    });
    rerender({ value: [...board] });

    expect(loaded).toEqual(['/media/a.webp']);
  });
});
