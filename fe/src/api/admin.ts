import { z } from 'zod';

import {
  type AdminUserSortEnum,
  GameStats,
  PaginatedAdminUsers,
  PaginatedCategoryStats,
  ServerStatus,
  type UserRole,
} from '@/schemas';
import { request } from './http';

export interface AdminUserSearch {
  role?: UserRole;
  username?: string;
  created_from?: string;
  created_to?: string;
  sort?: AdminUserSortEnum;
}

export async function searchAdminUsers(filters: AdminUserSearch, page: number, size: number) {
  return request('/admin/users', PaginatedAdminUsers, {
    search: { ...filters, page, size },
  });
}

export async function promoteUser(id: number) {
  return request(`/admin/users/${id}/promote`, z.void(), { method: 'POST' });
}

export async function deleteUser(id: number) {
  return request(`/admin/users/${id}`, z.void(), { method: 'DELETE' });
}

export async function getServerStatus() {
  return request('/admin/server', ServerStatus);
}

export async function getGameStats() {
  return request('/admin/stats', GameStats);
}

export async function getCategoryStats(page: number, size: number) {
  return request('/admin/stats/categories', PaginatedCategoryStats, { search: { page, size } });
}
