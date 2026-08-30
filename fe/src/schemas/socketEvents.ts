import { z } from 'zod';

// Client → server payloads (mirror be/src/schemas/socket/events.py)
export const SelectStarterPayload = z.object({ user_id: z.number().int() });
export type SelectStarterPayload = z.infer<typeof SelectStarterPayload>;

export const SelectPromptPayload = z.object({ prompt_id: z.number().int() });
export type SelectPromptPayload = z.infer<typeof SelectPromptPayload>;

export const JudgeAnswerPayload = z.object({ correct: z.boolean() });
export type JudgeAnswerPayload = z.infer<typeof JudgeAnswerPayload>;

export const BanPlayerPayload = z.object({ user_id: z.number().int() });
export type BanPlayerPayload = z.infer<typeof BanPlayerPayload>;

export const UnbanPlayerPayload = z.object({ user_id: z.number().int() });
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
