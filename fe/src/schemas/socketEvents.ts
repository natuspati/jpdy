import { z } from 'zod';

export const SubmitFinalWagerPayload = z.object({
  amount: z.number().int().nonnegative().nullable(),
  command_id: z.string().uuid().optional(),
});
export type SubmitFinalWagerPayload = z.infer<typeof SubmitFinalWagerPayload>;

export const SubmitFinalAnswerPayload = z.object({
  answer: z.string().max(256),
  command_id: z.string().uuid().optional(),
});
export type SubmitFinalAnswerPayload = z.infer<typeof SubmitFinalAnswerPayload>;

export const JudgeFinalAnswerPayload = z.object({
  user_id: z.number().int(),
  correct: z.boolean(),
  command_id: z.string().uuid().optional(),
});
export type JudgeFinalAnswerPayload = z.infer<typeof JudgeFinalAnswerPayload>;

export const AdvanceFinalRevealPayload = z.object({
  user_id: z.number().int(),
  command_id: z.string().uuid().optional(),
});
export type AdvanceFinalRevealPayload = z.infer<typeof AdvanceFinalRevealPayload>;

// Client → server payloads (mirror be/src/schemas/socket/events.py)
export const SelectStarterPayload = z.object({
  user_id: z.number().int(),
  command_id: z.string().uuid().optional(),
});
export type SelectStarterPayload = z.infer<typeof SelectStarterPayload>;

export const SelectPromptPayload = z.object({
  prompt_id: z.number().int(),
  command_id: z.string().uuid().optional(),
});
export type SelectPromptPayload = z.infer<typeof SelectPromptPayload>;

export const PlaceBetPayload = z.object({
  amount: z.number().int(),
  command_id: z.string().uuid().optional(),
});
export type PlaceBetPayload = z.infer<typeof PlaceBetPayload>;

export const JudgeAnswerPayload = z.object({
  correct: z.boolean(),
  command_id: z.string().uuid().optional(),
});
export type JudgeAnswerPayload = z.infer<typeof JudgeAnswerPayload>;

export const BanPlayerPayload = z.object({
  user_id: z.number().int(),
  command_id: z.string().uuid().optional(),
});
export type BanPlayerPayload = z.infer<typeof BanPlayerPayload>;

export const StartGamePayload = z.object({
  force: z.boolean().optional(),
  command_id: z.string().uuid().optional(),
});
export type StartGamePayload = z.infer<typeof StartGamePayload>;

export const SetAssetsLoadedPayload = z.object({
  loaded: z.boolean(),
  command_id: z.string().uuid().optional(),
});
export type SetAssetsLoadedPayload = z.infer<typeof SetAssetsLoadedPayload>;

export const UnbanPlayerPayload = z.object({
  user_id: z.number().int(),
  command_id: z.string().uuid().optional(),
});
export type UnbanPlayerPayload = z.infer<typeof UnbanPlayerPayload>;

// Server → client error
export const SocketErrorPayload = z.object({
  code: z.string(),
  detail: z.string(),
});
export type SocketErrorPayload = z.infer<typeof SocketErrorPayload>;

export const GameSoundCuePayload = z
  .object({
    cue_id: z.number().int().positive(),
    cue: z.enum([
      'game_started',
      'clue_selected',
      'buzz_accepted',
      'answer_correct',
      'answer_wrong',
      'answer_expired',
      'answer_revealed',
      'game_completed',
    ]),
  })
  .strict();
export type GameSoundCuePayload = z.infer<typeof GameSoundCuePayload>;

export const LobbyDeletedPayload = z
  .object({
    lobby_id: z.number().int().positive(),
  })
  .strict();
export type LobbyDeletedPayload = z.infer<typeof LobbyDeletedPayload>;
