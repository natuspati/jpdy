interface PageInfo {
  page: number;
  size: number;
  total: number;
}

/** `getNextPageParam` for offset-paginated endpoints. */
export const nextPageParam = (last: PageInfo): number | undefined =>
  (last.page + 1) * last.size < last.total ? last.page + 1 : undefined;

/**
 * Flattens loaded pages, dropping repeated ids: offset paging can repeat a row when an item moves
 * to the top between page loads.
 */
export const flattenPages = <T extends { id: number }>(
  pages: ReadonlyArray<{ contents: T[] }>,
): T[] => [
  ...new Map(pages.flatMap((page) => page.contents).map((item) => [item.id, item])).values(),
];
