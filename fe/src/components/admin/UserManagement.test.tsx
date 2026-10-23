import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { AdminUser } from '@/schemas';
import UserManagement from './UserManagement';

const { useAdminUsers, promote, remove, users } = vi.hoisted(() => ({
  useAdminUsers: vi.fn(),
  promote: vi.fn(),
  remove: vi.fn(),
  users: { data: [] as AdminUser[] },
}));

vi.mock('@/hooks/useAdmin', () => ({
  useAdminUsers: (filters: unknown) => {
    useAdminUsers(filters);
    return {
      data: users.data,
      isLoading: false,
      isError: false,
      hasNextPage: false,
      isFetchingNextPage: false,
      fetchNextPage: vi.fn(),
    };
  },
  usePromoteUser: () => ({ isPending: false, mutateAsync: promote }),
  useDeleteUser: () => ({ isPending: false, mutateAsync: remove }),
}));
vi.mock('@/hooks/useAuth', () => ({ useAuth: () => ({ userId: 1 }) }));

const user = (id: number, username: string, role: AdminUser['role'] = 'generic'): AdminUser => ({
  id,
  username,
  role,
  created_at: '2026-01-10T12:00:00Z',
  lobbies_played: 3,
  lobbies_hosted: 2,
});

const lastFilters = () => useAdminUsers.mock.calls.at(-1)?.[0];

describe('UserManagement', () => {
  beforeEach(() => {
    useAdminUsers.mockClear();
    promote.mockReset().mockResolvedValue(undefined);
    remove.mockReset().mockResolvedValue(undefined);
    users.data = [user(1, 'me', 'admin'), user(2, 'other', 'admin'), user(3, 'bob')];
  });

  it('starts with newest-first and no other filters', () => {
    render(<UserManagement />);

    expect(lastFilters()).toEqual({
      role: undefined,
      username: undefined,
      created_from: undefined,
      created_to: undefined,
      sort: 'created_at_desc',
    });
  });

  it('sends role, sort and date filters', () => {
    render(<UserManagement />);

    fireEvent.change(screen.getByLabelText('Role'), { target: { value: 'generic' } });
    fireEvent.change(screen.getByLabelText('Sort'), { target: { value: 'username_asc' } });
    fireEvent.change(screen.getByLabelText('From'), { target: { value: '2026-01-01' } });
    fireEvent.change(screen.getByLabelText('To'), { target: { value: '2026-01-31' } });

    expect(lastFilters()).toEqual({
      role: 'generic',
      username: undefined,
      created_from: '2026-01-01',
      created_to: '2026-01-31',
      sort: 'username_asc',
    });
  });

  it('debounces the username search', async () => {
    render(<UserManagement />);

    await userEvent.type(screen.getByRole('searchbox', { name: 'Search users' }), 'bo');

    // nothing is searched until typing pauses
    expect(useAdminUsers.mock.calls.every(([f]) => f.username === undefined)).toBe(true);
    await waitFor(() => expect(lastFilters().username).toBe('bo'));
    expect(useAdminUsers.mock.calls.some(([f]) => f.username === 'b')).toBe(false);
  });

  it('offers promote and delete only where they are allowed', () => {
    render(<UserManagement />);

    // admins (including yourself) can be neither promoted nor deleted
    expect(screen.queryByRole('button', { name: 'Promote me' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Delete me' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Promote other' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Delete other' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Promote bob' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Delete bob' })).toBeInTheDocument();
  });

  it('never offers delete on your own row, even if you are not an admin row', () => {
    users.data = [user(1, 'me')];
    render(<UserManagement />);

    expect(screen.queryByRole('button', { name: 'Delete me' })).not.toBeInTheDocument();
  });

  it('confirms before promoting and before deleting', async () => {
    render(<UserManagement />);

    await userEvent.click(screen.getByRole('button', { name: 'Promote bob' }));
    expect(promote).not.toHaveBeenCalled();
    await userEvent.click(
      within(screen.getByRole('dialog')).getByRole('button', { name: 'Promote' }),
    );
    expect(promote).toHaveBeenCalledWith(3);

    await userEvent.click(screen.getByRole('button', { name: 'Delete bob' }));
    expect(remove).not.toHaveBeenCalled();
    await userEvent.click(
      within(screen.getByRole('dialog')).getByRole('button', { name: 'Delete' }),
    );
    expect(remove).toHaveBeenCalledWith(3);
  });
});
