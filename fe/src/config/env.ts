import { z } from 'zod';

const EnvSchema = z.object({
  VITE_API_URL: z.string().min(1).default('/api/v1'),
  VITE_SOCKET_URL: z.string().default(''),
  VITE_SOCKET_PATH: z.string().min(1).default('/ws'),
});

const parsed = EnvSchema.safeParse(import.meta.env);
if (!parsed.success) {
  throw new Error(`Invalid environment variables: ${JSON.stringify(parsed.error.issues)}`);
}

export const env = {
  API_URL: parsed.data.VITE_API_URL,
  SOCKET_URL: parsed.data.VITE_SOCKET_URL || 'http://localhost:8000',
  SOCKET_PATH: parsed.data.VITE_SOCKET_PATH,
} as const;
