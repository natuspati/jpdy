import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { useAuthStore } from '@/store/authStore';
import { useToastStore } from '@/store/toastStore';
import SignInForm from './SignInForm';

function makeToken(sub: number, exp: number): string {
  const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' })).replace(/=+$/, '');
  const payload = btoa(JSON.stringify({ sub, exp })).replace(/=+$/, '');
  return `${header}.${payload}.sig`;
}

const renderWithQueryClient = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <SignInForm />
    </QueryClientProvider>,
  );
};

describe('SignInForm', () => {
  beforeEach(() => {
    useAuthStore.getState().signOut();
    useToastStore.getState().clear();
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('shows zod errors for empty fields', async () => {
    renderWithQueryClient();
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }));
    expect(await screen.findAllByText(/required/i)).toHaveLength(2);
  });

  it('stores token on success', async () => {
    const token = makeToken(42, 2_000_000_000);
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        new Response(JSON.stringify({ access_token: token, token_type: 'bearer' }), {
          status: 200,
          headers: { 'content-type': 'application/json' },
        }),
      ),
    );
    renderWithQueryClient();
    await userEvent.type(screen.getByLabelText(/username/i), 'alice');
    await userEvent.type(screen.getByLabelText(/password/i), 'pw');
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }));
    await waitFor(() => expect(useAuthStore.getState().userId).toBe(42));
  });

  it('shows error detail toast on API error', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        new Response(JSON.stringify({ detail: 'bad creds' }), {
          status: 401,
          headers: { 'content-type': 'application/json' },
        }),
      ),
    );
    renderWithQueryClient();
    await userEvent.type(screen.getByLabelText(/username/i), 'alice');
    await userEvent.type(screen.getByLabelText(/password/i), 'pw');
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }));
    await waitFor(() => {
      const toasts = useToastStore.getState().toasts;
      expect(toasts.some((t) => t.text.includes('bad creds'))).toBe(true);
    });
  });
});
