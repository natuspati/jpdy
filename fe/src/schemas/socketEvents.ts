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
