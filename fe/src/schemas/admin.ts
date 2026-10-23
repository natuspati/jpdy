import { z } from 'zod';

import { UserRole } from './enums';
import { Paginated } from './pagination';

// AdminUserListItemSchema
export const AdminUser = z.object({
  id: z.number().int(),
  username: z.string(),
  role: UserRole,
  created_at: z.string(),
  lobbies_played: z.number().int().nonnegative(),
  lobbies_hosted: z.number().int().nonnegative(),
});
export type AdminUser = z.infer<typeof AdminUser>;

export const PaginatedAdminUsers = Paginated(AdminUser);
export type PaginatedAdminUsers = z.infer<typeof PaginatedAdminUsers>;
