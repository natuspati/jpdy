import { z } from 'zod';

import { MediaAsset, type MediaKind } from '@/schemas';
import { request } from './http';

export async function uploadMedia(file: File, kind: MediaKind): Promise<MediaAsset> {
  const form = new FormData();
  form.set('file', file);
  form.set('kind', kind);
  return request('/media', MediaAsset, { method: 'POST', multipartBody: form });
}

export async function deleteMedia(id: number): Promise<void> {
  return request(`/media/${id}`, z.void(), { method: 'DELETE' });
}
