import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { z } from 'zod';

import { useAuthStore } from '@/store/authStore';
import { ApiError } from './errors';
import { request } from './http';

const SampleSchema = z.object({ ok: z.boolean() });

function mockFetch(impl: typeof fetch) {
  vi.stubGlobal('fetch', vi.fn(impl));
}

describe('api/http request()', () => {
  beforeEach(() => {
    useAuthStore.getState().signOut();
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('attaches bearer token when present', async () => {
    useAuthStore.setState({
      token: 'abc',
      userId: 1,
      expiresAt: Date.now() + 100_000,
    });
    let capturedInit: RequestInit | undefined;
    mockFetch(async (_url: RequestInfo | URL, init?: RequestInit) => {
      capturedInit = init;
      return new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      });
    });
    await request('/x', SampleSchema);
    const headers = capturedInit?.headers as Record<string, string> | undefined;
    expect(headers?.['Authorization']).toBe('Bearer abc');
  });

  it('throws ApiError on non-2xx and parses the BE error body', async () => {
    mockFetch(
      async () =>
        new Response(JSON.stringify({ detail: 'nope' }), {
          status: 403,
          headers: { 'content-type': 'application/json' },
        }),
    );
    await expect(request('/x', SampleSchema)).rejects.toBeInstanceOf(ApiError);
    try {
      await request('/x', SampleSchema);
    } catch (e) {
      expect(e).toBeInstanceOf(ApiError);
      expect((e as ApiError).status).toBe(403);
      expect((e as ApiError).detail).toBe('nope');
      expect((e as ApiError).code).toBe('forbidden');
    }
  });

  it('throws invalid_response when the body does not match the schema', async () => {
    mockFetch(
      async () =>
        new Response(JSON.stringify({ ok: 'not-a-bool' }), {
          status: 200,
          headers: { 'content-type': 'application/json' },
        }),
    );
    try {
      await request('/x', SampleSchema);
      throw new Error('expected throw');
    } catch (e) {
      expect(e).toBeInstanceOf(ApiError);
      expect((e as ApiError).code).toBe('invalid_response');
    }
  });

  it('signs out on 401', async () => {
    useAuthStore.setState({
      token: 'abc',
      userId: 1,
      expiresAt: Date.now() + 100_000,
    });
    mockFetch(
      async () =>
        new Response(JSON.stringify({ detail: 'expired' }), {
          status: 401,
          headers: { 'content-type': 'application/json' },
        }),
    );
    await expect(request('/x', SampleSchema)).rejects.toBeInstanceOf(ApiError);
    expect(useAuthStore.getState().token).toBeNull();
  });
});
