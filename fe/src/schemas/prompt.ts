import { z } from 'zod';

import { Paginated } from './pagination';

// NUM_PROMPTS_IN_CATEGORY mirrors be constants
export const NUM_PROMPTS_IN_CATEGORY = 5;

// PromptInDBSchema
export const PromptInDB = z.object({
  id: z.number().int(),
  question: z.string(),
  question_type: z.literal('text'),
  answer: z.string(),
  answer_type: z.literal('text'),
  category_id: z.number().int(),
  order: z.number().int().nullable(),
});
export type PromptInDB = z.infer<typeof PromptInDB>;

// PromptCreateSchema
export const PromptCreate = z.object({
  question: z.string().min(1).max(256),
  question_type: z.literal('text'),
  answer: z.string().min(1).max(256),
  answer_type: z.literal('text'),
  order: z.number().int().min(1).max(NUM_PROMPTS_IN_CATEGORY),
});
export type PromptCreate = z.infer<typeof PromptCreate>;

// PromptUpdateSchema — partial with all-non-null fields
export const PromptUpdate = z
  .object({
    question: z.string().min(1).max(256).optional(),
    question_type: z.literal('text').optional(),
    answer: z.string().min(1).max(256).optional(),
    answer_type: z.literal('text').optional(),
  })
  .refine((d) => Object.keys(d).length > 0, { message: 'No fields to update' });
export type PromptUpdate = z.infer<typeof PromptUpdate>;

// PromptCategoryInDBSchema
export const PromptCategoryInDB = z.object({
  id: z.number().int(),
  name: z.string(),
  owner_id: z.number().int().nullable(),
  updated_at: z.string(),
});
export type PromptCategoryInDB = z.infer<typeof PromptCategoryInDB>;

// PromptCategoryWithPromptsInDBSchema
export const PromptCategoryWithPrompts = PromptCategoryInDB.extend({
  prompts: z.array(PromptInDB),
});
export type PromptCategoryWithPrompts = z.infer<typeof PromptCategoryWithPrompts>;

// PromptCategoryCreateSchema
export const PromptCategoryCreate = z.object({
  name: z.string().min(1, 'Required').max(256),
});
export type PromptCategoryCreate = z.infer<typeof PromptCategoryCreate>;

// PromptCategoryUpdateSchema
export const PromptCategoryUpdate = z
  .object({
    name: z.string().min(1).max(256).optional(),
    prompt_order: z.record(z.string(), z.number().int()).optional(),
  })
  .refine((d) => Object.keys(d).length > 0, { message: 'No fields to update' });
export type PromptCategoryUpdate = z.infer<typeof PromptCategoryUpdate>;

export const PaginatedPromptCategories = Paginated(PromptCategoryWithPrompts);
export type PaginatedPromptCategories = z.infer<typeof PaginatedPromptCategories>;
