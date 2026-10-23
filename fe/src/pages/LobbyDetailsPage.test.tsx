import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import type { LobbyDetails } from '@/schemas';
import LobbyDetailsPage from './LobbyDetailsPage';

const { lobby } = vi.hoisted(() => ({ lobby: { current: null as LobbyDetails | null } }));

vi.mock('@/hooks/useLobbies', () => ({
  useLobby: () => ({ data: lobby.current, isLoading: false, isError: false }),
}));

const completedLobby: LobbyDetails = {
  id: 7,
  owner_id: 1,
  state: 'completed',
  created_at: '2026-09-01T00:00:00Z',
  updated_at: '2026-09-01T00:00:00Z',
  owner: { id: 1, username: 'host' },
  prompt_categories: [],
  player_count: 2,
  is_owner: true,
  is_participant: false,
  final_rankings: [
    { user_id: 2, username: 'ann', final_score: 900, is_banned: false, rank: 1 },
    { user_id: 3, username: 'bob', final_score: 100, is_banned: false, rank: 2 },
  ],
  rounds: [
    {
      round_number: 1,
      kind: 'standard',
      categories: [],
      results: [{ user_id: 2, username: 'ann', score: 900, score_delta: 900, is_banned: false }],
    },
  ],
};

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/lobby/7/details']}>
      <Routes>
        <Route path="/" element={<p>Lobbies home</p>} />
        <Route path="/lobby/:id/details" element={<LobbyDetailsPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('LobbyDetailsPage', () => {
  it('shows only the lobby id as title, with a labelled back arrow that returns home', () => {
    lobby.current = completedLobby;
    renderPage();

    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Lobby #7');
    expect(screen.queryByText('Lobby details')).not.toBeInTheDocument();
    expect(screen.getByRole('tooltip', { name: 'Back to lobbies' })).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Back to lobbies' }));
    expect(screen.getByText('Lobbies home')).toBeInTheDocument();
  });

  it('shows host, state, players and categories, without the removed copy', () => {
    lobby.current = completedLobby;
    renderPage();

    for (const label of ['Host', 'State', 'Players', 'Categories']) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }
    expect(screen.queryByText('Category list')).not.toBeInTheDocument();
    expect(screen.queryByText(/lobby metadata only/)).not.toBeInTheDocument();
  });

  it('puts the final rankings above the round breakdowns', () => {
    lobby.current = completedLobby;
    renderPage();

    const rankings = screen.getByRole('heading', { name: 'Final rankings' });
    const round = screen.getByRole('region', { name: 'Round 1' });
    expect(rankings.compareDocumentPosition(round) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });
});
