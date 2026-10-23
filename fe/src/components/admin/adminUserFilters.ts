import type { AdminUserSearch } from '@/api/admin';
import type { AdminUserSortEnum, UserRole } from '@/schemas';

export interface AdminUserFilters {
  role: 'all' | UserRole;
  username: string;
  createdFrom: string;
  createdTo: string;
}

export type AdminUserSortColumn =
  | 'username'
  | 'role'
  | 'created_at'
  | 'lobbies_played'
  | 'lobbies_hosted';

export const DEFAULT_ADMIN_USER_FILTERS: AdminUserFilters = {
  role: 'all',
  username: '',
  createdFrom: '',
  createdTo: '',
};

/** How many filters other than the username search differ from their defaults. */
export const activeAdminFilterCount = (filters: AdminUserFilters): number =>
  Number(filters.role !== DEFAULT_ADMIN_USER_FILTERS.role) +
  Number(filters.createdFrom !== '') +
  Number(filters.createdTo !== '');

export const toAdminUserSearch = (
  filters: AdminUserFilters,
  sort: AdminUserSortEnum | null,
): AdminUserSearch => ({
  role: filters.role === 'all' ? undefined : filters.role,
  username: filters.username.trim() || undefined,
  created_from: filters.createdFrom || undefined,
  created_to: filters.createdTo || undefined,
  sort: sort ?? undefined,
});
