import { z } from 'zod';

import {
  BanPlayerPayload,
  JudgeAnswerPayload,
  SelectPromptPayload,
  SelectStarterPayload,
  UnbanPlayerPayload,
} from '@/schemas';
import { toastError } from '@/store/toastStore';
import type { LobbySocket } from './client';
import type { ClientEventName, ClientToServerEvents } from './types';

const payloadSchemas: Partial<Record<ClientEventName, z.ZodTypeAny>> = {
  select_starter: SelectStarterPayload,
  select_prompt: SelectPromptPayload,
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
  const commandId = crypto.randomUUID();
  const eventArgs: unknown[] =
    args.length > 0
      ? [
          {
            ...(args[0] as object),
            command_id: commandId,
          },
        ]
      : [{ command_id: commandId }];
  // Socket.IO's emit implementation reads instance state through `this`, so
  // bind it before crossing the generic spread boundary.
  const emitFn = socket.emit.bind(socket) as unknown as (e: string, ...rest: unknown[]) => unknown;
  emitFn(event, ...eventArgs);
  return true;
}
