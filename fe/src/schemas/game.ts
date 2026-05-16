import { z } from 'zod';

import { GamePhaseEnum, PlayerConnectionStatusEnum } from './enums';

// Mirrors GameHostState
export const GameHostState = z.object({
  user_id: z.number().int(),
  username: z.string(),
  connection_status: PlayerConnectionStatusEnum.default('disconnected'),
});
export type GameHostState = z.infer<typeof GameHostState>;

// Mirrors GamePlayerState
export const GamePlayerState = z.object({
  user_id: z.number().int(),
  username: z.string(),
  score: z.number().int().default(0),
  connection_status: PlayerConnectionStatusEnum.default('disconnected'),
  is_selected: z.boolean().default(false),
  is_banned: z.boolean().default(false),
});
export type GamePlayerState = z.infer<typeof GamePlayerState>;

// Mirrors GamePromptState
export const GamePromptState = z.object({
  prompt_id: z.number().int(),
  question: z.string(),
  answer: z.string(),
  order: z.number().int(),
  is_selected: z.boolean().default(false),
  score_value: z.number().int(),
});
export type GamePromptState = z.infer<typeof GamePromptState>;

// Mirrors GameCategoryState
export const GameCategoryState = z.object({
  category_id: z.number().int(),
  name: z.string(),
  prompts: z.array(GamePromptState),
});
export type GameCategoryState = z.infer<typeof GameCategoryState>;

// Mirrors GameLobbyState
export const GameLobbyState = z.object({
  lobby_id: z.number().int(),
  host: GameHostState,
  players: z.array(GamePlayerState).default([]),
  categories: z.array(GameCategoryState).default([]),
  phase: GamePhaseEnum.default('waiting_for_players'),
  current_prompt_id: z.number().int().nullable().default(null),
  selecting_player_id: z.number().int().nullable().default(null),
  answering_player_id: z.number().int().nullable().default(null),
  attempted_player_ids: z.array(z.number().int()).default([]),
  last_submitted_answer: z.string().nullable().default(null),
  timer_deadline: z.string().nullable().default(null),
});
export type GameLobbyState = z.infer<typeof GameLobbyState>;
