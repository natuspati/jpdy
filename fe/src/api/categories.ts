import { z } from 'zod';

import {
  PaginatedPromptCategories,
  PromptCategoryCreate,
  PromptCategoryInDB,
  PromptCategoryUpdate,
  PromptCategoryWithPrompts,
  PromptCreate,
  PromptInDB,
  PromptUpdate,
} from '@/schemas';
import { request } from './http';

interface CategoryFilters {
  page?: number;
  size?: number;
  name?: string;
  owner_ids?: number[];
  is_complete?: boolean;
}

export async function searchCategories(filters: CategoryFilters = {}) {
  return request('/category', PaginatedPromptCategories, { search: { ...filters } });
}

export async function getCategory(id: number) {
  return request(`/category/${id}`, PromptCategoryWithPrompts);
}

export async function createCategory(payload: PromptCategoryCreate) {
  return request('/category', PromptCategoryInDB, { method: 'POST', body: payload });
}

export async function updateCategory(id: number, payload: PromptCategoryUpdate) {
  return request(`/category/${id}`, PromptCategoryWithPrompts, {
    method: 'PATCH',
    body: payload,
  });
}

export async function deleteCategory(id: number) {
  return request(`/category/${id}`, z.void(), { method: 'DELETE' });
}

export async function createPrompt(categoryId: number, payload: PromptCreate) {
  return request(`/category/${categoryId}/prompts`, PromptInDB, {
    method: 'POST',
    body: payload,
  });
}

export async function updatePrompt(categoryId: number, promptId: number, payload: PromptUpdate) {
  return request(`/category/${categoryId}/prompts/${promptId}`, PromptInDB, {
    method: 'PATCH',
    body: payload,
  });
}

export async function deletePrompt(categoryId: number, promptId: number) {
  return request(`/category/${categoryId}/prompts/${promptId}`, z.void(), { method: 'DELETE' });
}
