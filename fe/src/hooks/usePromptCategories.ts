import {
  keepPreviousData,
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query';

import {
  createCategory,
  createPrompt,
  deleteCategory,
  deletePrompt,
  getCategory,
  searchCategories,
  updateCategory,
  updatePrompt,
} from '@/api/categories';
import { ApiError } from '@/api/errors';
import { queryKeys } from '@/api/queryKeys';
import { useAuth } from '@/hooks/useAuth';
import type {
  PromptCategoryCreate,
  PromptCategoryKindEnum,
  PromptCategorySortEnum,
  PromptCategoryUpdate,
  PromptCreate,
  PromptUpdate,
} from '@/schemas';
import { toastError, toastSuccess } from '@/store/toastStore';
import { flattenPages, nextPageParam } from '@/utils/pagination';

export const MY_CATEGORIES_PAGE_SIZE = 30;

interface MyCategoryFilters {
  is_complete?: boolean;
  kind?: PromptCategoryKindEnum;
  sort?: PromptCategorySortEnum;
  name?: string;
}

/** The viewer's own categories, loaded page by page; a different filter set starts a new list. */
export function useMyCategories(filters: MyCategoryFilters = {}) {
  const { userId, isAuthed } = useAuth();
  const merged = { ...filters, owner_ids: userId ? [userId] : undefined };
  return useInfiniteQuery({
    queryKey: queryKeys.categories.mine(merged),
    queryFn: ({ pageParam }) =>
      searchCategories({ ...merged, page: pageParam, size: MY_CATEGORIES_PAGE_SIZE }),
    initialPageParam: 0,
    getNextPageParam: nextPageParam,
    select: ({ pages }) => flattenPages(pages),
    enabled: isAuthed,
  });
}

/** Ready categories, the viewer's own first, then most recently updated; optional name search. */
export function useAvailableCategories(kind: PromptCategoryKindEnum = 'standard', name?: string) {
  const { isAuthed } = useAuth();
  const filters = {
    is_complete: true,
    size: 200,
    kind,
    sort: 'own_first' as const,
    name: name || undefined,
  };
  return useQuery({
    queryKey: queryKeys.categories.list(filters),
    queryFn: () => searchCategories(filters),
    enabled: isAuthed,
    placeholderData: keepPreviousData,
  });
}

export function useCategory(id: number | undefined) {
  return useQuery({
    queryKey: id ? queryKeys.categories.detail(id) : ['categories', 'detail', 'none'],
    queryFn: () => getCategory(id as number),
    enabled: id !== undefined,
  });
}

export function useCreateCategory() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: PromptCategoryCreate) => createCategory(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.categories.all() });
      toastSuccess('Category created');
    },
    onError: (e) => toastError(e instanceof ApiError ? e.detail : 'Failed to create category'),
  });
}

export function useUpdateCategory(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: PromptCategoryUpdate) => updateCategory(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.categories.all() });
    },
    onError: (e) => toastError(e instanceof ApiError ? e.detail : 'Failed to update category'),
  });
}

export function useDeleteCategory() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => deleteCategory(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.categories.all() });
      toastSuccess('Category deleted');
    },
    onError: (e) => toastError(e instanceof ApiError ? e.detail : 'Failed to delete category'),
  });
}

export function useCreatePrompt(categoryId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: PromptCreate) => createPrompt(categoryId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.categories.all() });
    },
    onError: (e) => toastError(e instanceof ApiError ? e.detail : 'Failed to create prompt'),
  });
}

export function useUpdatePrompt(categoryId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ promptId, payload }: { promptId: number; payload: PromptUpdate }) =>
      updatePrompt(categoryId, promptId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.categories.all() });
    },
    onError: (e) => toastError(e instanceof ApiError ? e.detail : 'Failed to update prompt'),
  });
}

export function useDeletePrompt(categoryId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (promptId: number) => deletePrompt(categoryId, promptId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.categories.all() });
    },
    onError: (e) => toastError(e instanceof ApiError ? e.detail : 'Failed to delete prompt'),
  });
}
