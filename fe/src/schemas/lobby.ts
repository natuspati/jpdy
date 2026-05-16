import { z } from 'zod';

import { LobbyStateEnum } from './enums';
import { Paginated } from './pagination';
import { PromptCategoryInDB } from './prompt';
import { UserPublic } from './user';

// LobbyInDBSchema
export const LobbyInDB = z.object({
  id: z.number().int(),
  owner_id: z.number().int().nullable(),
  state: LobbyStateEnum,
  created_at: z.string(),
  updated_at: z.string(),
});
export type LobbyInDB = z.infer<typeof LobbyInDB>;

// LobbyWithCategoriesInDBSchema
export const LobbyWithCategories = LobbyInDB.extend({
  owner: UserPublic.nullable(),
  prompt_categories: z.array(PromptCategoryInDB),
});
export type LobbyWithCategories = z.infer<typeof LobbyWithCategories>;

// LobbyUpdateSchema — at least one set
export const LobbyUpdate = z
  .object({
    state: LobbyStateEnum.optional(),
    prompt_category_ids: z.array(z.number().int()).optional(),
  })
  .refine((d) => Object.keys(d).length > 0, { message: 'No fields to update' });
export type LobbyUpdate = z.infer<typeof LobbyUpdate>;

export const PaginatedLobbies = Paginated(LobbyWithCategories);
export type PaginatedLobbies = z.infer<typeof PaginatedLobbies>;

export const LobbyFilter = z.object({
  page: z.number().int().min(0).default(0),
  size: z.number().int().min(1).max(1000).default(100),
  ids: z.array(z.number().int()).optional(),
  owner_ids: z.array(z.number().int()).optional(),
  owner_username: z.string().min(1).max(20).optional(),
  states: z.array(LobbyStateEnum).optional(),
  updated_at_start: z.string().optional(),
  updated_at_end: z.string().optional(),
});
export type LobbyFilter = z.infer<typeof LobbyFilter>;
