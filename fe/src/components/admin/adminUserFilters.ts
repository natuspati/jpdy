import type { AdminUserSearch } from '@/api/admin';
import type { AdminUserSortEnum, UserRole } from '@/schemas';

export interface AdminUserFilters {
  role: 'all' | UserRole;
  username: string;
  createdFrom: string;
  createdTo: string;
  sort: AdminUserSortEnum;
}

export const DEFAULT_ADMIN_USER_FILTERS: AdminUserFilters = {
  role: 'all',
  username: '',
  createdFrom: '',
  createdTo: '',
  sort: 'created_at_desc',
};

/** How many filters other than the username search differ from their defaults. */
export const activeAdminFilterCount = (filters: AdminUserFilters): number =>
  Number(filters.role !== DEFAULT_ADMIN_USER_FILTERS.role) +
  Number(filters.createdFrom !== '') +
  Number(filters.createdTo !== '') +
  Number(filters.sort !== DEFAULT_ADMIN_USER_FILTERS.sort);

export const toAdminUserSearch = (filters: AdminUserFilters): AdminUserSearch => ({
  role: filters.role === 'all' ? undefined : filters.role,
  username: filters.username.trim() || undefined,
  created_from: filters.createdFrom || undefined,
  created_to: filters.createdTo || undefined,
  sort: filters.sort,
});
