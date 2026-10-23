import { z } from 'zod';

export const PromptCategoryKindEnum = z.enum(['standard', 'final']);
export type PromptCategoryKindEnum = z.infer<typeof PromptCategoryKindEnum>;

// Mirrors be/src/enums/prompt.py
export const PromptCategorySortEnum = z.enum([
  'updated_desc',
  'updated_asc',
  'name_asc',
  'name_desc',
  'own_first',
]);
export type PromptCategorySortEnum = z.infer<typeof PromptCategorySortEnum>;

// Mirrors be/src/enums/user.py
export const UserRole = z.enum(['generic', 'admin']);
export type UserRole = z.infer<typeof UserRole>;

// Mirrors be/src/enums/lobby.py
export const LobbyStateEnum = z.enum(['created', 'waiting_start', 'in_progress', 'completed']);
export type LobbyStateEnum = z.infer<typeof LobbyStateEnum>;

// Mirrors be/src/enums/game.py
export const GamePhaseEnum = z.enum([
  'waiting_for_players',
  'host_selecting_starting_player',
  'player_selecting_prompt',
  'betting_announcement',
  'betting_open',
  'player_answering',
  'buzz_open',
  'answer_reveal',
  'round_summary',
  'final_betting',
  'final_answering',
  'final_reveal',
  'finished',
]);
export type GamePhaseEnum = z.infer<typeof GamePhaseEnum>;

export const GameResolutionEnum = z.enum(['correct', 'unanswered', 'expired']);
export type GameResolutionEnum = z.infer<typeof GameResolutionEnum>;

export const PlayerConnectionStatusEnum = z.enum(['connected', 'disconnected']);
export type PlayerConnectionStatusEnum = z.infer<typeof PlayerConnectionStatusEnum>;

// Mirrors AdminUserSortEnum in be/src/enums/user.py
export const AdminUserSortEnum = z.enum([
  'username_asc',
  'username_desc',
  'created_at_asc',
  'created_at_desc',
]);
export type AdminUserSortEnum = z.infer<typeof AdminUserSortEnum>;

// Mirrors be/src/enums/admin.py
export const HealthStatusEnum = z.enum(['ok', 'degraded', 'down']);
export type HealthStatusEnum = z.infer<typeof HealthStatusEnum>;
