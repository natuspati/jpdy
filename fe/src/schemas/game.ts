import { z } from 'zod';

import {
  GamePhaseEnum,
  GameResolutionEnum,
  PlayerConnectionStatusEnum,
  PromptCategoryKindEnum,
} from './enums';
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
  assets_loaded: z.boolean().default(false),
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
    answer_media: MediaReference.nullable().optional(),
    order: z.number().int(),
    is_selected: z.boolean().default(false),
    score_value: z.number().int().nullable(),
    is_betting: z.boolean().default(false),
  })
  .strict();
export type GamePromptState = z.infer<typeof GamePromptState>;

// Mirrors PublicGameCategoryState
export const GameCategoryState = z.object({
  category_id: z.number().int(),
  name: z.string(),
  kind: PromptCategoryKindEnum.default('standard'),
  round_number: z.number().int().positive().default(1),
  prompts: z.array(GamePromptState),
});
export type GameCategoryState = z.infer<typeof GameCategoryState>;

// Mirrors GameRoundScore: cumulative score after the round plus what the round earned.
export const GameRoundScore = z.object({
  user_id: z.number().int(),
  username: z.string(),
  score: z.number().int(),
  score_delta: z.number().int(),
  is_banned: z.boolean().default(false),
});
export type GameRoundScore = z.infer<typeof GameRoundScore>;

// Mirrors GameRoundResult
export const GameRoundResult = z.object({
  round_number: z.number().int().positive(),
  scores: z.array(GameRoundScore).default([]),
});
export type GameRoundResult = z.infer<typeof GameRoundResult>;

export const FinalPlayerState = z
  .object({
    user_id: z.number().int(),
    username: z.string(),
    score_before_final: z.number().int(),
    decision_submitted: z.boolean(),
    answer_submitted: z.boolean(),
    removed: z.boolean(),
    revealed: z.boolean(),
    wager: z.number().int().positive().nullable(),
    answer: z.string().max(256).nullable(),
    correct: z.boolean().nullable(),
    score_delta: z.number().int().nullable(),
    updated_score: z.number().int().nullable(),
  })
  .strict();
export type FinalPlayerState = z.infer<typeof FinalPlayerState>;

export const FinalRoundState = z
  .object({
    players: z.array(FinalPlayerState),
    current_user_id: z.number().int().nullable(),
    is_last_reveal: z.boolean(),
    skipped_reason: z.string().nullable(),
    correct_answer: z.string().nullable(),
    correct_answer_type: PromptContentType.nullable(),
    correct_answer_media: MediaReference.nullable(),
  })
  .strict();
export type FinalRoundState = z.infer<typeof FinalRoundState>;

// Mirrors GameLobbyState
export const GameLobbyState = z
  .object({
    lobby_id: z.number().int(),
    state_revision: z.number().int().nonnegative().default(0),
    host: GameHostState,
    players: z.array(GamePlayerState).default([]),
    categories: z.array(GameCategoryState).default([]),
    phase: GamePhaseEnum.default('waiting_for_players'),
    current_round: z.number().int().positive().default(1),
    total_rounds: z.number().int().positive().default(1),
    round_results: z.array(GameRoundResult).default([]),
    final_round: FinalRoundState.nullable().default(null),
    current_prompt_id: z.number().int().nullable().default(null),
    selecting_player_id: z.number().int().nullable().default(null),
    answering_player_id: z.number().int().nullable().default(null),
    attempted_player_ids: z.array(z.number().int()).default([]),
    min_bet: z.number().int().nonnegative().default(0),
    max_bet: z.number().int().nonnegative().default(0),
    my_bet: z.number().int().nonnegative().nullable().default(null),
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
      state.resolution !== null ||
      state.resolved_answer_type != null ||
      state.resolved_answer_media != null;

    const invalid = (message: string): void => {
      context.addIssue({ code: z.ZodIssueCode.custom, message });
    };
    const final = state.final_round;
    const isFinal = ['final_betting', 'final_answering', 'final_reveal'].includes(state.phase);
    if (isFinal && !final) invalid('Final phases require final_round');
    if (
      isFinal &&
      (state.selecting_player_id !== null ||
        state.answering_player_id !== null ||
        state.my_bet !== null)
    )
      invalid('Final phases cannot use normal selector, answerer, or auction state');
    if (
      (state.phase === 'final_betting' || state.phase === 'final_answering') &&
      (state.timer_deadline === null || !Number.isFinite(Date.parse(state.timer_deadline)))
    ) {
      invalid('Final submissions require a valid shared deadline');
    }
    if (state.phase === 'final_betting' && state.current_prompt_id !== null) {
      invalid('Final betting cannot expose the current question');
    }
    if (
      (state.phase === 'final_answering' || state.phase === 'final_reveal') &&
      !state.categories.some(
        (category) =>
          category.kind === 'final' &&
          category.round_number === state.current_round &&
          category.prompts.some((prompt) => prompt.prompt_id === state.current_prompt_id),
      )
    )
      invalid('Final answering and reveal require the current Final prompt');
    if (state.phase === 'final_reveal' && state.timer_deadline !== null) {
      invalid('Final reveal is untimed');
    }
    if (final && !isFinal && state.phase !== 'finished') {
      invalid('final_round is only public during the Final or after completion');
    }
    if (final?.skipped_reason != null && state.phase !== 'finished') {
      invalid('A skipped Final must be finished');
    }
    const questionVisible =
      state.phase === 'final_answering' ||
      state.phase === 'final_reveal' ||
      (state.phase === 'finished' && final !== null && final.skipped_reason === null);
    // Bans can redact every previously revealed row from a completed player snapshot.
    const canonicalVisible =
      state.phase === 'final_reveal' ||
      (state.phase === 'finished' && final !== null && final.skipped_reason === null);
    for (const category of state.categories) {
      for (const prompt of category.prompts) {
        if (category.kind !== 'final') {
          if (prompt.score_value === null) invalid('Standard prompts require a score');
          continue;
        }
        if (prompt.score_value !== null || prompt.is_betting) {
          invalid('Final prompts cannot have a fixed score or auction');
        }
        if (!questionVisible && (prompt.question !== '' || prompt.question_media != null)) {
          invalid('Final question is hidden until answering');
        }
        if (!canonicalVisible && prompt.answer_media != null) {
          invalid('Final answer media is hidden until reveal');
        }
      }
    }
    if (final) {
      if (
        !canonicalVisible &&
        (final.correct_answer !== null ||
          final.correct_answer_type !== null ||
          final.correct_answer_media !== null)
      )
        invalid('Final canonical answer is hidden until reveal');
      if (
        state.phase === 'final_reveal' &&
        (final.correct_answer === null ||
          final.correct_answer_type === null ||
          !final.players.some(
            (player) =>
              player.user_id === final.current_user_id && player.revealed && !player.removed,
          ))
      )
        invalid('Final reveal requires a current revealed player and canonical answer');
      if (
        (state.phase === 'final_betting' || state.phase === 'final_answering') &&
        (final.current_user_id !== null || final.players.some((player) => player.revealed))
      ) {
        invalid('Final responses cannot be revealed before final_reveal');
      }
      for (const player of final.players) {
        if (
          state.phase === 'final_betting' &&
          (player.answer !== null || player.answer_submitted || player.correct !== null)
        ) {
          invalid('Final answers cannot precede answering');
        }
        if (
          player.wager !== null &&
          (!player.decision_submitted || player.wager > player.score_before_final)
        ) {
          invalid('Final wager requires a decision within the starting score');
        }
        if (player.answer !== null && !player.answer_submitted && player.answer.trim() !== '') {
          invalid('Final answer requires a submission');
        }
        if (player.correct !== null) {
          if (
            !player.revealed ||
            player.wager === null ||
            player.score_delta !== (player.correct ? player.wager : -player.wager) ||
            player.updated_score !== player.score_before_final + player.score_delta
          ) {
            invalid('Final judgment requires a revealed response and consistent outcome');
          }
        } else if (player.score_delta !== null || player.updated_score !== null) {
          invalid('Final score outcomes require judgment');
        }
      }
    }

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
