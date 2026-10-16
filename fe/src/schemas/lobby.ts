import { z } from 'zod';

import { LobbyStateEnum } from './enums';
import { Paginated } from './pagination';
import { MAX_BETTING_PROMPTS_PER_ROUND, PromptCategoryInDB } from './prompt';
import { UserPublic } from './user';

// LobbyInDBSchema
export const LobbyInDB = z.object({
  id: z.number().int(),
  owner_id: z.number().int().nullable(),
  state: LobbyStateEnum,
  created_at: z.string(),
  updated_at: z.string(),
  // null means the default share of each round's prompts.
  betting_prompt_count: z.number().int().nullable().optional(),
});
export type LobbyInDB = z.infer<typeof LobbyInDB>;

// LobbyWithCategoriesInDBSchema
export const LobbyWithCategories = LobbyInDB.extend({
  owner: UserPublic.nullable(),
  prompt_categories: z.array(PromptCategoryInDB),
  player_count: z.number().int().nonnegative().nullable(),
});
export type LobbyWithCategories = z.infer<typeof LobbyWithCategories>;

export const ActiveLobby = z.object({
  id: z.number().int(),
  host_username: z.string(),
  player_count: z.number().int().nonnegative(),
  state: z.literal('waiting_start'),
  created_at: z.string(),
  can_join: z.boolean(),
});
export type ActiveLobby = z.infer<typeof ActiveLobby>;

export const MyLobby = z.object({
  id: z.number().int(),
  owner_id: z.number().int().nullable(),
  host_username: z.string().nullable(),
  player_count: z.number().int().nonnegative(),
  state: LobbyStateEnum,
  created_at: z.string(),
  updated_at: z.string(),
  is_owner: z.boolean(),
  is_participant: z.boolean(),
});
export type MyLobby = z.infer<typeof MyLobby>;

export const LobbyFinalRanking = z.object({
  user_id: z.number().int().nullable(),
  username: z.string(),
  final_score: z.number().int(),
  is_banned: z.boolean(),
  rank: z.number().int().positive(),
});
export type LobbyFinalRanking = z.infer<typeof LobbyFinalRanking>;

// LobbyRoundResultSchema
export const LobbyRoundResult = z.object({
  user_id: z.number().int().nullable(),
  username: z.string(),
  score: z.number().int(),
  score_delta: z.number().int(),
  is_banned: z.boolean(),
});
export type LobbyRoundResult = z.infer<typeof LobbyRoundResult>;

// LobbyRoundSchema; `results` is null until the lobby is completed.
export const LobbyRound = z.object({
  round_number: z.number().int().positive(),
  categories: z.array(PromptCategoryInDB),
  results: z.array(LobbyRoundResult).nullable(),
});
export type LobbyRound = z.infer<typeof LobbyRound>;

export const LobbyDetails = LobbyWithCategories.extend({
  is_owner: z.boolean(),
  is_participant: z.boolean(),
  final_rankings: z.array(LobbyFinalRanking).nullable(),
  rounds: z.array(LobbyRound).default([]),
});
export type LobbyDetails = z.infer<typeof LobbyDetails>;

// LobbyUpdateSchema — at least one set
export const LobbyUpdate = z
  .object({
    state: LobbyStateEnum.optional(),
    // Category ids per round; list index + 1 is the round number.
    rounds: z.array(z.array(z.number().int())).optional(),
    // Betting prompts per round; null resets to the default.
    betting_prompt_count: z
      .number()
      .int()
      .min(0)
      .max(MAX_BETTING_PROMPTS_PER_ROUND)
      .nullable()
      .optional(),
  })
  .refine((d) => Object.keys(d).length > 0, { message: 'No fields to update' });
export type LobbyUpdate = z.infer<typeof LobbyUpdate>;

export const PaginatedLobbies = Paginated(LobbyWithCategories);
export type PaginatedLobbies = z.infer<typeof PaginatedLobbies>;

export const LobbyFilter = z.object({
  page: z.number().int().min(0).default(0),
  size: z.number().int().min(1).max(1000).default(100),
  ids: z.array(z.number().int()).optional(),
  owner_ids: z.array(z.number().int()).optional(),
  owner_username: z.string().min(1).max(20).optional(),
  states: z.array(LobbyStateEnum).optional(),
  updated_at_start: z.string().optional(),
  updated_at_end: z.string().optional(),
});
export type LobbyFilter = z.infer<typeof LobbyFilter>;
