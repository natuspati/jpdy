import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useAuthStore } from '@/store/authStore';
import AdminRoute from './AdminRoute';

const { me } = vi.hoisted(() => ({
  me: {
    data: undefined as { role: 'generic' | 'admin'; admin_key_attempted: boolean } | undefined,
    isError: false,
  },
}));

vi.mock('@/hooks/useMe', () => ({ useMe: () => me }));
vi.mock('@/components/admin/AdminKeyModal', () => ({ default: () => <p>key modal</p> }));

const Home = () => {
  const { pathname, state } = useLocation();
  return (
    <p>
      home {pathname} {JSON.stringify(state)}
    </p>
  );
};

const renderRoute = () =>
  render(
    <MemoryRouter initialEntries={['/admin']}>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route
          path="/admin"
          element={
            <AdminRoute>
              <p>admin page</p>
            </AdminRoute>
          }
        />
      </Routes>
    </MemoryRouter>,
  );

const signIn = () =>
  useAuthStore.setState({ token: 't', userId: 1, expiresAt: Date.now() + 60_000 });

describe('AdminRoute', () => {
  beforeEach(() => {
    useAuthStore.getState().signOut();
    me.data = undefined;
    me.isError = false;
  });

  it('sends a signed-out visitor to sign-in and remembers the page', () => {
    renderRoute();
    expect(screen.getByText(/home \//)).toHaveTextContent('"from":"/admin"');
  });

  it('shows a spinner, never the key modal, while the role loads', () => {
    signIn();
    renderRoute();
    expect(screen.getByRole('status', { name: 'Loading' })).toBeInTheDocument();
    expect(screen.queryByText('key modal')).not.toBeInTheDocument();
  });

  it('renders the page for an admin', () => {
    signIn();
    me.data = { role: 'admin', admin_key_attempted: true };
    renderRoute();
    expect(screen.getByText('admin page')).toBeInTheDocument();
  });

  it('asks a generic user who still has an attempt for the key', () => {
    signIn();
    me.data = { role: 'generic', admin_key_attempted: false };
    renderRoute();
    expect(screen.getByText('key modal')).toBeInTheDocument();
    expect(screen.queryByText('admin page')).not.toBeInTheDocument();
  });

  it('silently redirects a generic user whose attempt is spent', () => {
    signIn();
    me.data = { role: 'generic', admin_key_attempted: true };
    renderRoute();
    expect(screen.getByText(/home \//)).toBeInTheDocument();
    expect(screen.queryByText('key modal')).not.toBeInTheDocument();
  });
});
