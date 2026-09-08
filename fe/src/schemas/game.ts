import { z } from 'zod';

import { GamePhaseEnum, GameResolutionEnum, PlayerConnectionStatusEnum } from './enums';
import { MediaReference } from './media';
import { PromptContentType } from './prompt';

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

// Mirrors the player-visible PublicGamePromptState. Expected answers are never
// included in a broadcast state frame.
export const GamePromptState = z
  .object({
    prompt_id: z.number().int(),
    question: z.string(),
    question_type: PromptContentType.optional(),
    question_media: MediaReference.nullable().optional(),
    order: z.number().int(),
    is_selected: z.boolean().default(false),
    score_value: z.number().int(),
  })
  .strict();
export type GamePromptState = z.infer<typeof GamePromptState>;

// Mirrors GameCategoryState
export const GameCategoryState = z.object({
  category_id: z.number().int(),
  name: z.string(),
  prompts: z.array(GamePromptState),
});
export type GameCategoryState = z.infer<typeof GameCategoryState>;

// Mirrors GameLobbyState
export const GameLobbyState = z
  .object({
    lobby_id: z.number().int(),
    state_revision: z.number().int().nonnegative().default(0),
    host: GameHostState,
    players: z.array(GamePlayerState).default([]),
    categories: z.array(GameCategoryState).default([]),
    phase: GamePhaseEnum.default('waiting_for_players'),
    current_prompt_id: z.number().int().nullable().default(null),
    selecting_player_id: z.number().int().nullable().default(null),
    answering_player_id: z.number().int().nullable().default(null),
    attempted_player_ids: z.array(z.number().int()).default([]),
    timer_deadline: z.string().nullable().default(null),
    resolved_prompt_id: z.number().int().nullable().default(null),
    resolved_answer: z.string().nullable().default(null),
    resolution: GameResolutionEnum.nullable().default(null),
    resolved_answer_type: PromptContentType.nullable().optional(),
    resolved_answer_media: MediaReference.nullable().optional(),
    latest_sound_cue_id: z.number().int().nonnegative().optional(),
  })
  .strict()
  .superRefine((state, context) => {
    const hasResolutionData =
      state.resolved_prompt_id !== null ||
      state.resolved_answer !== null ||
      state.resolution !== null;

    if (state.phase === 'answer_reveal') {
      if (
        state.resolved_prompt_id === null ||
        state.resolved_answer === null ||
        state.resolution === null
      ) {
        context.addIssue({
          code: z.ZodIssueCode.custom,
          message: 'answer_reveal requires complete resolution data',
        });
      }
      return;
    }

    if (hasResolutionData) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        message: 'resolution data is only public during answer_reveal',
      });
    }
  });
export type GameLobbyState = z.infer<typeof GameLobbyState>;

// Mirrors host-only `host_answer_key`. Never present in public state frames.
export const HostAnswerKey = z
  .object({
    lobby_id: z.number().int(),
    prompt_id: z.number().int(),
    expected_answer: z.string(),
  })
  .strict();
export type HostAnswerKey = z.infer<typeof HostAnswerKey>;
