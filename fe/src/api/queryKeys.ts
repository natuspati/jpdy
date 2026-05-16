import type { LobbyFilter } from '@/schemas';

/**
 * Typed factory for TanStack Query keys. Centralizing lets us invalidate by
 * prefix from mutations without typoing strings everywhere.
 */
export const queryKeys = {
  me: () => ['me'] as const,
  lobbies: {
    all: () => ['lobbies'] as const,
    list: (filters: Partial<LobbyFilter>) => ['lobbies', 'list', filters] as const,
    detail: (id: number) => ['lobbies', 'detail', id] as const,
  },
  categories: {
    all: () => ['categories'] as const,
    list: (filters: Record<string, unknown>) => ['categories', 'list', filters] as const,
    detail: (id: number) => ['categories', 'detail', id] as const,
  },
} as const;
