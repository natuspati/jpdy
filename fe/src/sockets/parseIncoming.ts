import { z } from 'zod';

import { GameLobbyState, HostAnswerKey, SocketErrorPayload } from '@/schemas';

interface ParseResult<T> {
  ok: boolean;
  data?: T;
  issues?: z.ZodIssue[];
}

export function parseStateChanged(raw: unknown): ParseResult<GameLobbyState> {
  const parsed = GameLobbyState.safeParse(raw);
  if (!parsed.success) {
    console.error('[socket] invalid state_changed payload', parsed.error.issues);
    return { ok: false, issues: parsed.error.issues };
  }
  return { ok: true, data: parsed.data };
}

export function parseSocketError(raw: unknown): ParseResult<SocketErrorPayload> {
  const parsed = SocketErrorPayload.safeParse(raw);
  if (!parsed.success) {
    console.error('[socket] invalid error payload', parsed.error.issues);
    return { ok: false, issues: parsed.error.issues };
  }
  return { ok: true, data: parsed.data };
}

export function parseHostAnswerKey(raw: unknown): ParseResult<HostAnswerKey> {
  const parsed = HostAnswerKey.safeParse(raw);
  if (!parsed.success) {
    console.error('[socket] invalid host_answer_key payload', parsed.error.issues);
    return { ok: false, issues: parsed.error.issues };
  }
  return { ok: true, data: parsed.data };
}
