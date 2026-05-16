import { beforeEach, describe, expect, it } from 'vitest';

import { isAuthenticated, useAuthStore } from './authStore';

// JWT with sub=42, exp=2_000_000_000 (year 2033); HS256, no signature verification on client.
// Built once at test time below.

function makeToken(sub: number, exp: number): string {
  const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' })).replace(/=+$/, '');
  // Encode `sub` as a string to match how the BE issues JWTs.
  const payload = btoa(JSON.stringify({ sub: String(sub), exp })).replace(/=+$/, '');
  return `${header}.${payload}.signature`;
}

describe('authStore', () => {
  beforeEach(() => {
    useAuthStore.getState().signOut();
  });

  it('stores token and decodes sub/exp', () => {
    const token = makeToken(42, 2_000_000_000);
    useAuthStore.getState().setToken(token);
    const state = useAuthStore.getState();
    expect(state.token).toBe(token);
    expect(state.userId).toBe(42);
    expect(state.expiresAt).toBe(2_000_000_000_000);
  });

  it('signOut clears the store', () => {
    useAuthStore.getState().setToken(makeToken(42, 2_000_000_000));
    useAuthStore.getState().signOut();
    const state = useAuthStore.getState();
    expect(state.token).toBeNull();
    expect(state.userId).toBeNull();
    expect(state.expiresAt).toBeNull();
  });

  it('isAuthenticated returns false for expired token', () => {
    useAuthStore.getState().setToken(makeToken(42, 1));
    expect(isAuthenticated(useAuthStore.getState())).toBe(false);
  });

  it('rejects malformed tokens', () => {
    useAuthStore.getState().setToken('garbage');
    expect(useAuthStore.getState().token).toBeNull();
  });
});
