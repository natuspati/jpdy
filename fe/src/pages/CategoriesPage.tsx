import { useCallback, useState } from 'react';

import CategoryCard from '@/components/categories/CategoryCard';
import CategoryFilterBar from '@/components/categories/CategoryFilterBar';
import {
  DEFAULT_CATEGORY_LIST_FILTERS,
  activeFilterCount,
} from '@/components/categories/categoryFilters';
import CreateCategoryModal from '@/components/categories/CreateCategoryModal';
import NewItemButton from '@/components/ui/NewItemButton';
import Spinner from '@/components/ui/Spinner';
import { useDebouncedValue } from '@/hooks/useDebouncedValue';
import { useInfiniteScroll } from '@/hooks/useInfiniteScroll';
import { useMyCategories } from '@/hooks/usePromptCategories';

const SEARCH_DEBOUNCE_MS = 300;

const CategoriesPage = () => {
  const [open, setOpen] = useState(false);
  const [filters, setFilters] = useState(DEFAULT_CATEGORY_LIST_FILTERS);
  const search = useDebouncedValue(filters.search.trim(), SEARCH_DEBOUNCE_MS);
  const {
    data: categories = [],
    isLoading,
    hasNextPage,
    isFetchingNextPage,
    fetchNextPage,
  } = useMyCategories({
    is_complete: filters.readiness === 'all' ? undefined : filters.readiness === 'complete',
    kind: filters.kind === 'all' ? undefined : filters.kind,
    sort: filters.sort,
    name: search || undefined,
  });
  const loadMore = useCallback(() => void fetchNextPage(), [fetchNextPage]);
  const sentinelRef = useInfiniteScroll(loadMore, hasNextPage && !isFetchingNextPage);
  const isFiltered = activeFilterCount(filters) > 0 || search !== '';

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-x-2 gap-y-3">
        <h1 className="text-2xl font-bold">My categories</h1>
        <div className="max-sm:ml-auto">
          <NewItemButton label="New category" onClick={() => setOpen(true)} />
        </div>
        <div className="flex w-full justify-end sm:ml-auto sm:w-auto">
          <CategoryFilterBar value={filters} onChange={setFilters} />
        </div>
      </div>

      {isLoading ? (
        <Spinner />
      ) : categories.length === 0 ? (
        <p className="text-slate-400">
          {isFiltered ? 'No categories match your filters.' : 'No categories yet.'}
        </p>
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {categories.map((c) => (
            <CategoryCard key={c.id} category={c} />
          ))}
        </div>
      )}
      {isFetchingNextPage ? (
        <div className="flex justify-center">
          <Spinner />
        </div>
      ) : null}
      <div ref={sentinelRef} aria-hidden className="h-px" />

      <CreateCategoryModal open={open} onClose={() => setOpen(false)} />
    </div>
  );
};

export default CategoriesPage;
