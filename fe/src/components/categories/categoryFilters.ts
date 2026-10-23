import type { PromptCategoryKindEnum, PromptCategorySortEnum } from '@/schemas';

export interface CategoryListFilters {
  readiness: 'all' | 'complete' | 'incomplete';
  kind: 'all' | PromptCategoryKindEnum;
  sort: PromptCategorySortEnum;
  search: string;
}

export const DEFAULT_CATEGORY_LIST_FILTERS: CategoryListFilters = {
  readiness: 'all',
  kind: 'all',
  sort: 'updated_desc',
  search: '',
};

/** How many of the select filters differ from their defaults (search is shown separately). */
export const activeFilterCount = (filters: CategoryListFilters): number =>
  Number(filters.readiness !== DEFAULT_CATEGORY_LIST_FILTERS.readiness) +
  Number(filters.kind !== DEFAULT_CATEGORY_LIST_FILTERS.kind) +
  Number(filters.sort !== DEFAULT_CATEGORY_LIST_FILTERS.sort);
