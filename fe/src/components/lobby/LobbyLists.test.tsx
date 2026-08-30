import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen } from '@testing-library/react';
import { type ReactNode } from 'react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import { formatLocalDateTime } from '@/utils/formatDateTime';
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
    const createdAt = '2026-01-01T00:00:00Z';
    renderList(
      <ActiveLobbyList
        loading={false}
        error={false}
        onCreateLobby={vi.fn()}
        lobbies={[
          {
            id: 12,
            host_username: 'alex',
            player_count: 3,
            state: 'waiting_start',
            created_at: createdAt,
            can_join: true,
          },
        ]}
      />,
    );

    expect(screen.getByText('#12')).toBeInTheDocument();
    expect(screen.getByText('alex')).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: 'Created at' })).toBeInTheDocument();
    expect(screen.getByText(formatLocalDateTime(createdAt))).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Join' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Show details' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Delete' })).not.toBeInTheDocument();
  });

  it('opens the new lobby creation flow from the active-lobbies heading', () => {
    const onCreateLobby = vi.fn();
    renderList(
      <ActiveLobbyList loading={false} error={false} lobbies={[]} onCreateLobby={onCreateLobby} />,
    );

    const newLobbyButton = screen.getByRole('button', { name: 'New lobby' });
    expect(newLobbyButton).toHaveAttribute('title', 'New lobby');
    expect(screen.getByRole('tooltip', { name: 'New lobby' })).toBeInTheDocument();

    fireEvent.click(newLobbyButton);
    expect(onCreateLobby).toHaveBeenCalledOnce();
  });

  it('renders compact, labelled actions and a compact waiting state in my lobbies', () => {
    const createdAt = '2026-08-30T00:00:00Z';
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
            created_at: createdAt,
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
    expect(screen.queryByRole('button', { name: 'Join' })).not.toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: 'Show details' })[0]).toHaveTextContent('D');
    expect(screen.getByRole('button', { name: 'Delete' })).toHaveTextContent('X');
    expect(screen.getByRole('columnheader', { name: 'Created at' })).toBeInTheDocument();
    expect(
      screen
        .getAllByText(formatLocalDateTime(createdAt))
        .every((timestamp) => timestamp.textContent?.endsWith(':00')),
    ).toBe(true);
  });

  it('renders compact join actions and a waiting-state tooltip', () => {
    renderList(
      <MyLobbyList
        loading={false}
        error={false}
        lobbies={[
          {
            id: 6,
            owner_id: 1,
            host_username: 'host',
            player_count: 1,
            state: 'waiting_start',
            created_at: '2026-08-30T00:00:00Z',
            updated_at: '2026-08-30T00:00:00Z',
            is_owner: true,
            is_participant: false,
          },
          {
            id: 7,
            owner_id: 2,
            host_username: 'other-host',
            player_count: 2,
            state: 'in_progress',
            created_at: '2026-08-30T00:00:00Z',
            updated_at: '2026-08-30T00:00:00Z',
            is_owner: false,
            is_participant: true,
          },
        ]}
      />,
    );

    const joinButtons = screen.getAllByRole('button', { name: 'Join' });
    expect(joinButtons).toHaveLength(2);
    expect(joinButtons[0]).toHaveTextContent('J');
    expect(screen.getByText('Waiting...').closest('[title]')).toHaveAttribute(
      'title',
      'Waiting for players',
    );
    expect(screen.getByRole('tooltip', { name: 'Waiting for players' })).toBeInTheDocument();
  });
});
