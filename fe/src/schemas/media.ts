import { z } from 'zod';

export const MediaKind = z.enum(['image', 'audio', 'video']);
export type MediaKind = z.infer<typeof MediaKind>;

export const MediaReference = z.object({
  asset_id: z.number().int(),
  url: z.string().startsWith('/media/'),
  mime_type: z.string().min(1),
  filename: z.string().min(1),
});
export type MediaReference = z.infer<typeof MediaReference>;

export const MediaAsset = z.object({
  id: z.number().int(),
  owner_id: z.number().int().nullable(),
  storage_key: z.string().min(1),
  original_filename: z.string().min(1),
  media_kind: MediaKind,
  mime_type: z.string().min(1),
  byte_size: z.number().int().nonnegative(),
  duration_seconds: z.number().int().nullable(),
  width: z.number().int().nullable(),
  height: z.number().int().nullable(),
  created_at: z.string(),
  url: z.string().startsWith('/media/'),
});
export type MediaAsset = z.infer<typeof MediaAsset>;
