import { useEffect, useState } from 'react';

import type { GameCategoryState, GamePhaseEnum, MediaReference } from '@/schemas';

const MAX_CONCURRENT_FETCHES = 4;

// Media files are immutable. Fetching them into blobs keeps the whole game in memory, so a clue
// opens instantly and Safari never needs a range request to a cold cache.
// ponytail: holds every file in memory (up to 50 prompts x 2 files); evict or stream if that bites.
const blobUrls = new Map<string, string>();

/** Local blob URL for already preloaded media, or null to fall back to the network URL. */
export const preloadedSrc = (media: MediaReference | null | undefined): string | null =>
  (media && blobUrls.get(media.url)) ?? null;

const mediaUrls = (
  categories: GameCategoryState[] | undefined,
  phase: GamePhaseEnum | undefined,
  finalAnswerMedia: MediaReference | null | undefined,
): string[] => {
  const urls = new Set<string>();
  for (const category of categories ?? []) {
    if (
      category.kind === 'final' &&
      phase !== 'final_answering' &&
      phase !== 'final_reveal' &&
      phase !== 'finished'
    )
      continue;
    for (const prompt of category.prompts) {
      if (prompt.question_media) urls.add(prompt.question_media.url);
      if (
        prompt.answer_media &&
        (category.kind !== 'final' || phase === 'final_reveal' || phase === 'finished')
      ) {
        urls.add(prompt.answer_media.url);
      }
    }
  }
  if (finalAnswerMedia && (phase === 'final_reveal' || phase === 'finished')) {
    urls.add(finalAnswerMedia.url);
  }
  return [...urls];
};

export interface MediaPreloadProgress {
  loaded: number;
  total: number;
}

// A failed fetch counts as done: one broken asset must not block the game, and the player
// element still falls back to the network URL.
export const useBoardMediaPreload = (
  categories: GameCategoryState[] | undefined,
  phase?: GamePhaseEnum,
  finalAnswerMedia?: MediaReference | null,
): MediaPreloadProgress => {
  const urls = mediaUrls(categories, phase, finalAnswerMedia);
  const key = urls.join('\n');
  const [done, setDone] = useState<ReadonlySet<string>>(new Set());

  useEffect(() => {
    const controller = new AbortController();
    const queue = key ? key.split('\n') : [];
    const markDone = (url: string): void => {
      if (!controller.signal.aborted) setDone((prev) => new Set(prev).add(url));
    };
    const worker = async (): Promise<void> => {
      for (let url = queue.shift(); url !== undefined; url = queue.shift()) {
        if (!blobUrls.has(url)) {
          try {
            const response = await fetch(url, { signal: controller.signal });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            blobUrls.set(url, URL.createObjectURL(await response.blob()));
          } catch {
            // Aborted or failed: the element streams from the network URL instead.
          }
        }
        markDone(url);
      }
    };
    for (let i = 0; i < MAX_CONCURRENT_FETCHES; i += 1) void worker();
    return () => controller.abort();
  }, [key]);

  useEffect(
    () => () => {
      for (const blobUrl of blobUrls.values()) URL.revokeObjectURL(blobUrl);
      blobUrls.clear();
    },
    [],
  );

  return { loaded: urls.filter((url) => done.has(url)).length, total: urls.length };
};
