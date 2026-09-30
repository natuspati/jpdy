import { z } from 'zod';

import { MeResponse } from '@/schemas/me';
import { TokenResponse, UserPublic } from '@/schemas';
import { request } from './http';

export async function signIn(username: string, password: string): Promise<TokenResponse> {
  const formBody = new URLSearchParams();
  formBody.set('username', username);
  formBody.set('password', password);
  return request('/user/sign-in', TokenResponse, { method: 'POST', formBody });
}

export async function register(
  username: string,
  password: string,
  inviteCode: string,
): Promise<UserPublic> {
  return request('/user/register', UserPublic, {
    method: 'POST',
    body: { username, password, invite_code: inviteCode || null },
  });
}

export async function getMe(): Promise<MeResponse> {
  return request('/user/me', MeResponse);
}

export const SignInArgs = z.object({
  username: z.string(),
  password: z.string(),
});
