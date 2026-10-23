import { useEffect, useState } from 'react';

/**
 * Calls `onLoadMore` whenever the returned sentinel ref scrolls into view. Pass `enabled=false`
 * while a page is loading or when nothing is left: re-enabling re-arms the observer, so a
 * sentinel that is still visible after a page loads triggers the next one.
 */
export function useInfiniteScroll(onLoadMore: () => void, enabled: boolean) {
  const [sentinel, setSentinel] = useState<HTMLElement | null>(null);

  useEffect(() => {
    if (!sentinel || !enabled) return;
    const observer = new IntersectionObserver((entries) => {
      if (entries.some((entry) => entry.isIntersecting)) onLoadMore();
    });
    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [sentinel, enabled, onLoadMore]);

  return setSentinel;
}
