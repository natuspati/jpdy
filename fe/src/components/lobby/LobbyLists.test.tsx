import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { type ReactNode } from 'react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
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

const deleteLobby = vi.hoisted(() => vi.fn());

vi.mock('@/hooks/useLobbies', () => ({
  useDeleteLobby: () => ({ mutateAsync: deleteLobby, isPending: false }),
}));

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

  it('highlights live lobbies, has no action column and opens details for a finished lobby', () => {
    const base = {
      host_username: 'host',
      player_count: 1,
      created_at: '2026-08-30T00:00:00Z',
      updated_at: '2026-08-30T00:00:00Z',
      is_participant: false,
    };
    renderList(
      <>
        <MyLobbyList
          loading={false}
          error={false}
          hasMore={false}
          loadingMore={false}
          onLoadMore={vi.fn()}
          lobbies={[
            { ...base, id: 6, owner_id: 1, state: 'in_progress', is_owner: true },
            { ...base, id: 5, owner_id: 2, state: 'completed', is_owner: false },
          ]}
        />
        <Routes>
          <Route path="/lobby/:id/details" element={<p>Lobby details</p>} />
        </Routes>
      </>,
    );

    expect(screen.queryByRole('columnheader', { name: 'Action' })).not.toBeInTheDocument();
    expect(screen.getAllByRole('button')).toHaveLength(1);
    expect(screen.getByRole('button', { name: 'Delete lobby 6' })).toHaveTextContent('X');
    expect(screen.getByRole('columnheader', { name: 'Created at' })).toBeInTheDocument();
    expect(screen.getAllByText(formatLocalDateTime('2026-08-30T00:00:00Z'))).toHaveLength(2);
    expect(screen.getByRole('row', { name: 'Join lobby 6' })).toHaveClass('bg-amber-400/10');
    expect(screen.getByRole('row', { name: 'Show details of lobby 5' })).not.toHaveClass(
      'bg-amber-400/10',
    );

    fireEvent.click(screen.getByRole('row', { name: 'Show details of lobby 5' }));
    expect(screen.getByText('Lobby details')).toBeInTheDocument();
  });

  it('joins a live lobby from its row', () => {
    renderList(
      <>
        <MyLobbyList
          loading={false}
          error={false}
          hasMore={false}
          loadingMore={false}
          onLoadMore={vi.fn()}
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
          ]}
        />
        <Routes>
          <Route path="/lobby/:id" element={<p>Joined lobby</p>} />
        </Routes>
      </>,
    );

    expect(screen.getByText('Waiting...').closest('[title]')).toHaveAttribute(
      'title',
      'Waiting for players',
    );
    fireEvent.click(screen.getByRole('row', { name: 'Join lobby 6' }));
    expect(screen.getByText('Joined lobby')).toBeInTheDocument();
  });

  it('lets the host delete a live lobby from its row without joining it', async () => {
    deleteLobby.mockResolvedValue(undefined);
    renderList(
      <>
        <MyLobbyList
          loading={false}
          error={false}
          hasMore={false}
          loadingMore={false}
          onLoadMore={vi.fn()}
          lobbies={[
            {
              id: 6,
              owner_id: 1,
              host_username: 'host',
              player_count: 1,
              state: 'in_progress',
              created_at: '2026-08-30T00:00:00Z',
              updated_at: '2026-08-30T00:00:00Z',
              is_owner: true,
              is_participant: false,
            },
          ]}
        />
        <Routes>
          <Route path="/lobby/:id" element={<p>Joined lobby</p>} />
        </Routes>
      </>,
    );

    fireEvent.click(screen.getByRole('button', { name: 'Delete lobby 6' }));
    expect(screen.queryByText('Joined lobby')).not.toBeInTheDocument();
    expect(deleteLobby).not.toHaveBeenCalled();

    fireEvent.click(
      within(screen.getByRole('dialog')).getByRole('button', { name: 'Delete lobby' }),
    );
    await waitFor(() => expect(deleteLobby).toHaveBeenCalledWith(6));
    expect(screen.queryByText('Joined lobby')).not.toBeInTheDocument();
  });
});
