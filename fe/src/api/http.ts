import { z } from 'zod';

import { env } from '@/config/env';
import { useAuthStore } from '@/store/authStore';
import { ApiError } from './errors';

type Method = 'GET' | 'POST' | 'PATCH' | 'DELETE' | 'PUT';

interface RequestOptions<TBody = unknown> {
  method?: Method;
  body?: TBody;
  multipartBody?: FormData;
  formBody?: URLSearchParams;
  search?: Record<string, string | number | boolean | Array<string | number> | undefined | null>;
  signal?: AbortSignal;
}

function buildUrl(path: string, search: RequestOptions['search']): string {
  const base = env.API_URL.endsWith('/') ? env.API_URL.slice(0, -1) : env.API_URL;
  const suffix = path.startsWith('/') ? path : `/${path}`;
  const url = new URL(`${base}${suffix}`, window.location.origin);
  if (search) {
    for (const [key, value] of Object.entries(search)) {
      if (value === undefined || value === null) continue;
      if (Array.isArray(value)) {
        for (const v of value) url.searchParams.append(key, String(v));
      } else {
        url.searchParams.set(key, String(value));
      }
    }
  }
  return url.pathname + url.search;
}

/**
 * Make a REST call and validate the response with the supplied zod schema.
 *
 * The schema is the boundary contract — if the response doesn't match it,
 * we throw an `ApiError("invalid_response")` so TanStack Query surfaces it
 * via toast and we never cache garbage. Pass `z.void()` for endpoints that
 * return 204 / no body.
 */
export async function request<TSchema extends z.ZodTypeAny>(
  path: string,
  responseSchema: TSchema,
  options: RequestOptions = {},
): Promise<z.infer<TSchema>> {
  const url = buildUrl(path, options.search);
  const headers: Record<string, string> = {};
  const token = useAuthStore.getState().token;
  if (token) headers['Authorization'] = `Bearer ${token}`;

  let body: BodyInit | undefined;
  if (options.formBody) {
    headers['Content-Type'] = 'application/x-www-form-urlencoded';
    body = options.formBody;
  } else if (options.multipartBody) {
    body = options.multipartBody;
  } else if (options.body !== undefined) {
    headers['Content-Type'] = 'application/json';
    body = JSON.stringify(options.body);
  }

  let res: Response;
  try {
    res = await fetch(url, {
      method: options.method ?? 'GET',
      headers,
      body,
      signal: options.signal,
    });
  } catch (e) {
    throw new ApiError({
      status: 0,
      code: 'network_error',
      detail: e instanceof Error ? e.message : 'Network request failed',
    });
  }

  if (res.status === 401) {
    useAuthStore.getState().signOut();
  }

  if (!res.ok) {
    throw await ApiError.fromResponse(res);
  }

  if (res.status === 204) {
    return responseSchema.parse(undefined);
  }

  let json: unknown;
  try {
    json = await res.json();
  } catch {
    if (responseSchema instanceof z.ZodVoid) {
      return undefined as z.infer<TSchema>;
    }
    throw new ApiError({
      status: res.status,
      code: 'invalid_response',
      detail: 'Server returned an unparseable response',
    });
  }

  const parsed = responseSchema.safeParse(json);
  if (!parsed.success) {
    // Log full issues for the developer; show a generic toast to the user.
    console.error('[api] response schema mismatch', { path, issues: parsed.error.issues });
    throw new ApiError({
      status: res.status,
      code: 'invalid_response',
      detail: 'Server returned an unexpected response shape',
    });
  }
  return parsed.data;
}
