import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { renderHook, waitFor } from '@testing-library/react';
import type { PropsWithChildren } from 'react';
import { describe, expect, it, vi } from 'vitest';

import { searchCategories } from '@/api/categories';
import { useAvailableCategories } from './usePromptCategories';

vi.mock('@/api/categories', () => ({
  searchCategories: vi.fn(async () => ({ contents: [] })),
}));
vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({ isAuthed: true, userId: 1 }),
}));

describe('ready category selection', () => {
  it('requests standard and Final categories independently without sharing cache entries', async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const wrapper = ({ children }: PropsWithChildren) => (
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    );
    const { result } = renderHook(
      () => ({ standard: useAvailableCategories(), final: useAvailableCategories('final') }),
      { wrapper },
    );
    await waitFor(() => {
      expect(result.current.standard.isSuccess).toBe(true);
      expect(result.current.final.isSuccess).toBe(true);
    });
    expect(searchCategories).toHaveBeenCalledWith({
      kind: 'standard',
      is_complete: true,
      size: 200,
      sort: 'own_first',
    });
    expect(searchCategories).toHaveBeenCalledWith({
      kind: 'final',
      is_complete: true,
      size: 200,
      sort: 'own_first',
    });
  });
});
