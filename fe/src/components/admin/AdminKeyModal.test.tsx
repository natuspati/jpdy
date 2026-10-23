import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiError } from '@/api/errors';
import { queryKeys } from '@/api/queryKeys';
import { useToastStore } from '@/store/toastStore';
import AdminKeyModal from './AdminKeyModal';

const { claimAdminKey } = vi.hoisted(() => ({ claimAdminKey: vi.fn() }));
vi.mock('@/api/auth', () => ({ claimAdminKey }));

const renderModal = () => {
  const queryClient = new QueryClient({ defaultOptions: { mutations: { retry: false } } });
  const invalidate = vi.spyOn(queryClient, 'invalidateQueries');
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/admin']}>
        <Routes>
          <Route path="/" element={<p>home</p>} />
          <Route path="/admin" element={<AdminKeyModal />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
  return { invalidate };
};

const submit = async (key: string) => {
  await userEvent.type(screen.getByLabelText('Admin key'), key);
  await userEvent.click(screen.getByRole('button', { name: 'Continue' }));
};

describe('AdminKeyModal', () => {
  beforeEach(() => {
    claimAdminKey.mockReset();
    useToastStore.getState().clear();
  });

  it('refreshes the current user after a correct key', async () => {
    claimAdminKey.mockResolvedValue(undefined);
    const { invalidate } = renderModal();

    await submit('right-key');

    await waitFor(() => expect(invalidate).toHaveBeenCalledWith({ queryKey: queryKeys.me() }));
    expect(claimAdminKey).toHaveBeenCalledWith('right-key');
    expect(screen.queryByText('home')).not.toBeInTheDocument();
  });

  it('redirects home without any toast when the key is wrong', async () => {
    claimAdminKey.mockRejectedValue(
      new ApiError({ status: 403, code: 'forbidden', detail: 'Forbidden' }),
    );
    const { invalidate } = renderModal();

    await submit('guess');

    expect(await screen.findByText('home')).toBeInTheDocument();
    expect(useToastStore.getState().toasts).toEqual([]);
    expect(invalidate).toHaveBeenCalledWith({ queryKey: queryKeys.me() });
  });

  it('leaves on Escape without spending the attempt', async () => {
    renderModal();

    await userEvent.keyboard('{Escape}');

    expect(await screen.findByText('home')).toBeInTheDocument();
    expect(claimAdminKey).not.toHaveBeenCalled();
  });

  it('requires a key', async () => {
    renderModal();

    await userEvent.click(screen.getByRole('button', { name: 'Continue' }));

    expect(await screen.findByText('Required')).toBeInTheDocument();
    expect(claimAdminKey).not.toHaveBeenCalled();
  });
});
