import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { type ReactNode } from 'react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import ActiveLobbyList from './ActiveLobbyList';
import MyLobbyList from './MyLobbyList';

function renderList(children: ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('lobby lists', () => {
  it('renders active lobbies with only join actions', () => {
    renderList(
      <ActiveLobbyList
        loading={false}
        error={false}
        lobbies={[
          {
            id: 12,
            host_username: 'alex',
            player_count: 3,
            state: 'waiting_start',
            can_join: true,
          },
        ]}
      />,
    );

    expect(screen.getByText('#12')).toBeInTheDocument();
    expect(screen.getByText('alex')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Join' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Show details' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Delete' })).not.toBeInTheDocument();
  });

  it('renders owner-only delete action in my lobbies', () => {
    renderList(
      <MyLobbyList
        loading={false}
        error={false}
        lobbies={[
          {
            id: 4,
            owner_id: 1,
            host_username: 'host',
            player_count: 1,
            state: 'created',
            created_at: '2026-08-30T00:00:00Z',
            updated_at: '2026-08-30T00:00:00Z',
            is_owner: true,
            is_participant: false,
          },
          {
            id: 5,
            owner_id: 2,
            host_username: 'other-host',
            player_count: 2,
            state: 'completed',
            created_at: '2026-08-30T00:00:00Z',
            updated_at: '2026-08-30T00:00:00Z',
            is_owner: false,
            is_participant: true,
          },
        ]}
      />,
    );

    expect(screen.getAllByRole('button', { name: 'Show details' })).toHaveLength(2);
    expect(screen.getAllByRole('button', { name: 'Delete' })).toHaveLength(1);
  });
});
