import { z } from 'zod';

import { HealthStatusEnum, PromptCategoryKindEnum, UserRole } from './enums';
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

// GameStatsSchema
export const GameStats = z.object({
  active_lobbies: z.number().int().nonnegative(),
  active_players: z.number().int().nonnegative(),
  completed_lobbies: z.number().int().nonnegative(),
});
export type GameStats = z.infer<typeof GameStats>;

// CategoryStatsItemSchema
export const CategoryStat = z.object({
  id: z.number().int(),
  name: z.string(),
  kind: PromptCategoryKindEnum,
  lobbies_played: z.number().int().nonnegative(),
});
export type CategoryStat = z.infer<typeof CategoryStat>;

export const PaginatedCategoryStats = Paginated(CategoryStat);
export type PaginatedCategoryStats = z.infer<typeof PaginatedCategoryStats>;

// A probe that failed reports `down` and an error string; its other fields stay null.
const num = z.number().nullable();

export const RedisServer = z.object({
  status: HealthStatusEnum,
  error: z.string().nullable(),
  ping_ms: num,
  used_memory: num,
  maxmemory: num,
  connected_clients: num,
  ops_per_sec: num,
  uptime_seconds: num,
  evicted_keys: num,
  rejected_connections: num,
  game_state_keys: num,
});
export type RedisServer = z.infer<typeof RedisServer>;

export const DatabaseServer = z.object({
  status: HealthStatusEnum,
  error: z.string().nullable(),
  dialect: z.string().nullable(),
  ping_ms: num,
  pool_size: num,
  pool_checked_out: num,
  pool_overflow: num,
  user_count: num,
  lobby_count: num,
  category_count: num,
  size_bytes: num,
  active_connections: num,
});
export type DatabaseServer = z.infer<typeof DatabaseServer>;

export const BackendInstance = z.object({
  id: z.string(),
  hostname: z.string(),
  version: z.string(),
  started_at: z.string(),
  rss_bytes: z.number().int().nonnegative(),
});
export type BackendInstance = z.infer<typeof BackendInstance>;

export const BackendServer = z.object({
  status: HealthStatusEnum,
  error: z.string().nullable(),
  instances: z.array(BackendInstance),
  connected_sockets: num,
  live_games: num,
});
export type BackendServer = z.infer<typeof BackendServer>;

export const ServerStatus = z.object({
  status: HealthStatusEnum,
  redis: RedisServer,
  database: DatabaseServer,
  backend: BackendServer,
});
export type ServerStatus = z.infer<typeof ServerStatus>;
