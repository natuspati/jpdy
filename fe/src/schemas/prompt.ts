import { z } from 'zod';

import { Paginated } from './pagination';
import { MediaReference } from './media';

// NUM_PROMPTS_IN_CATEGORY mirrors be constants
export const NUM_PROMPTS_IN_CATEGORY = 5;
export const PromptContentType = z.enum(['text', 'image', 'audio', 'video']);
export type PromptContentType = z.infer<typeof PromptContentType>;

const QuestionContent = z.object({
  type: PromptContentType,
  text: z.string(),
  media: MediaReference.nullable(),
});

const AnswerContent = z.object({
  type: PromptContentType,
  text: z.string(),
  media: MediaReference.nullable(),
});

// PromptInDBSchema
export const PromptInDB = z.object({
  id: z.number().int(),
  question: z.string(),
  question_type: PromptContentType,
  answer: z.string(),
  answer_type: PromptContentType,
  question_media_asset_id: z.number().int().nullable(),
  answer_media_asset_id: z.number().int().nullable(),
  category_id: z.number().int(),
  order: z.number().int().nullable(),
  question_content: QuestionContent,
  answer_content: AnswerContent,
});
export type PromptInDB = z.infer<typeof PromptInDB>;

// PromptCreateSchema
export const PromptCreate = z
  .object({
    question: z.string().min(1).max(256),
    question_type: PromptContentType,
    answer: z.string().min(1).max(256),
    answer_type: PromptContentType,
    question_media_asset_id: z.number().int().nullable(),
    answer_media_asset_id: z.number().int().nullable(),
    order: z.number().int().min(1).max(NUM_PROMPTS_IN_CATEGORY),
  })
  .superRefine(validatePromptMedia);
export type PromptCreate = z.infer<typeof PromptCreate>;

// PromptUpdateSchema — partial with all-non-null fields
export const PromptUpdate = z
  .object({
    question: z.string().min(1).max(256).optional(),
    question_type: PromptContentType.optional(),
    answer: z.string().min(1).max(256).optional(),
    answer_type: PromptContentType.optional(),
    question_media_asset_id: z.number().int().nullable().optional(),
    answer_media_asset_id: z.number().int().nullable().optional(),
  })
  .refine((d) => Object.keys(d).length > 0, { message: 'No fields to update' });
export type PromptUpdate = z.infer<typeof PromptUpdate>;

function validatePromptMedia(
  value: {
    question_type: PromptContentType;
    answer_type: PromptContentType;
    question_media_asset_id: number | null;
    answer_media_asset_id: number | null;
  },
  context: z.RefinementCtx,
) {
  validateContentMedia(
    value.question_type,
    value.question_media_asset_id,
    'question_media_asset_id',
    context,
  );
  validateContentMedia(
    value.answer_type,
    value.answer_media_asset_id,
    'answer_media_asset_id',
    context,
  );
}

function validateContentMedia(
  type: PromptContentType,
  assetId: number | null,
  path: 'question_media_asset_id' | 'answer_media_asset_id',
  context: z.RefinementCtx,
) {
  const hasMedia = type !== 'text';
  if (hasMedia && assetId === null) {
    context.addIssue({ code: z.ZodIssueCode.custom, path: [path], message: 'Media required' });
  }
  if (!hasMedia && assetId !== null) {
    context.addIssue({
      code: z.ZodIssueCode.custom,
      path: [path],
      message: 'Text cannot use media',
    });
  }
}
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
