import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

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
  PromptCategoryUpdate,
  PromptCreate,
  PromptUpdate,
} from '@/schemas';
import { toastError, toastSuccess } from '@/store/toastStore';

interface CategoryFilters {
  page?: number;
  size?: number;
  is_complete?: boolean;
}

export function useMyCategories(filters: CategoryFilters = {}) {
  const { userId, isAuthed } = useAuth();
  const merged = { ...filters, owner_ids: userId ? [userId] : undefined };
  return useQuery({
    queryKey: queryKeys.categories.list(merged),
    queryFn: () => searchCategories(merged),
    enabled: isAuthed,
  });
}

export function useAvailableCategories() {
  const { isAuthed } = useAuth();
  return useQuery({
    queryKey: queryKeys.categories.list({ is_complete: true, size: 200 }),
    queryFn: () => searchCategories({ is_complete: true, size: 200 }),
    enabled: isAuthed,
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
    onError: (e) =>
      toastError(e instanceof ApiError ? e.detail : 'Failed to create category'),
  });
}

export function useUpdateCategory(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: PromptCategoryUpdate) => updateCategory(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.categories.all() });
    },
    onError: (e) =>
      toastError(e instanceof ApiError ? e.detail : 'Failed to update category'),
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
    onError: (e) =>
      toastError(e instanceof ApiError ? e.detail : 'Failed to delete category'),
  });
}

export function useCreatePrompt(categoryId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: PromptCreate) => createPrompt(categoryId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.categories.all() });
    },
    onError: (e) =>
      toastError(e instanceof ApiError ? e.detail : 'Failed to create prompt'),
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
    onError: (e) =>
      toastError(e instanceof ApiError ? e.detail : 'Failed to update prompt'),
  });
}

export function useDeletePrompt(categoryId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (promptId: number) => deletePrompt(categoryId, promptId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.categories.all() });
    },
    onError: (e) =>
      toastError(e instanceof ApiError ? e.detail : 'Failed to delete prompt'),
  });
}
