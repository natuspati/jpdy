import { z } from 'zod';

export const ApiErrorBody = z.object({
  detail: z
    .union([z.string(), z.array(z.unknown()), z.record(z.unknown())])
    .optional()
    .default('Request failed'),
});
export type ApiErrorBody = z.infer<typeof ApiErrorBody>;
