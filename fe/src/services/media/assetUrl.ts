import { env } from '@/config/env';

export function assetUrl(pathOrUrl: string): string {
  if (/^https?:\/\//i.test(pathOrUrl) || pathOrUrl.startsWith('data:')) return pathOrUrl;
  const base = env.MEDIA_URL.endsWith('/') ? env.MEDIA_URL.slice(0, -1) : env.MEDIA_URL;
  const suffix = pathOrUrl.startsWith('/') ? pathOrUrl : `/${pathOrUrl}`;
  return `${base}${suffix}`;
}
