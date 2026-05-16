import { z } from 'zod';

export const Paginated = <T extends z.ZodTypeAny>(item: T) =>
  z.object({
    contents: z.array(item).default([]),
    total: z.number().int().default(0),
    page: z.number().int().default(0),
    size: z.number().int().default(0),
  });

export const PaginationParams = z.object({
  page: z.number().int().min(0).default(0),
  size: z.number().int().min(1).max(1000).default(100),
});
export type PaginationParams = z.infer<typeof PaginationParams>;
