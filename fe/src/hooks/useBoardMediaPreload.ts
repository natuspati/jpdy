import { useEffect } from 'react';

import type { GameCategoryState } from '@/schemas';

// Media files are immutable, so loading them early fills the HTTP cache and the clue opens instantly.
const warmedImages = new Map<string, HTMLImageElement>();

// ponytail: images only. Audio/video are large and already stream via range requests;
// preload them too if their start-up delay becomes the next complaint.
export const useBoardMediaPreload = (categories: GameCategoryState[] | undefined): void => {
  useEffect(() => {
    for (const category of categories ?? []) {
      for (const prompt of category.prompts) {
        const media = prompt.question_media;
        if (!media?.mime_type.startsWith('image/') || warmedImages.has(media.url)) continue;
        const image = new Image();
        image.decoding = 'async';
        image.src = media.url;
        warmedImages.set(media.url, image);
      }
    }
  }, [categories]);
};
