import { z } from 'zod';

import {
  BanPlayerPayload,
  JudgeAnswerPayload,
  SelectPromptPayload,
  SelectStarterPayload,
  SubmitAnswerPayload,
  UnbanPlayerPayload,
} from '@/schemas';
import { toastError } from '@/store/toastStore';
import type { LobbySocket } from './client';
import type { ClientEventName, ClientToServerEvents } from './types';

const payloadSchemas: Partial<Record<ClientEventName, z.ZodTypeAny>> = {
  select_starter: SelectStarterPayload,
  select_prompt: SelectPromptPayload,
  submit_answer: SubmitAnswerPayload,
  judge_answer: JudgeAnswerPayload,
  ban_player: BanPlayerPayload,
  unban_player: UnbanPlayerPayload,
};

/**
 * Type-safe emit helper. For events with payloads we run zod on the payload
 * before emitting so the UI can't ship malformed data even if a caller
 * bypasses the form layer.
 */
export function emit<E extends ClientEventName>(
  socket: LobbySocket,
  event: E,
  ...args: Parameters<ClientToServerEvents[E]>
): boolean {
  const schema = payloadSchemas[event];
  if (schema) {
    const parsed = schema.safeParse(args[0]);
    if (!parsed.success) {
      toastError(`Invalid ${event} payload: ${parsed.error.issues[0]?.message ?? 'unknown'}`);
      return false;
    }
  }
  // socket.io types are not generic-friendly with the spread; cast at boundary.
  const emitFn = socket.emit as unknown as (e: string, ...rest: unknown[]) => unknown;
  emitFn(event, ...args);
  return true;
}
