import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { buildGameState } from '@/test/fixtures/gameState';
import FinalLeaderboard from './FinalLeaderboard';

describe('FinalLeaderboard', () => {
  it('sorts players by score descending', () => {
    const state = buildGameState({
      players: [
        { user_id: 2, username: 'alice', score: 300 },
        { user_id: 3, username: 'bob', score: 500 },
        { user_id: 4, username: 'carol', score: 100 },
      ],
    });
    render(<FinalLeaderboard state={state} />);
    const items = screen.getAllByRole('listitem').map((li) => li.textContent ?? '');
    expect(items[0]).toContain('bob');
    expect(items[1]).toContain('alice');
    expect(items[2]).toContain('carol');
  });

  it('shows the host as non-scoring', () => {
    const state = buildGameState();
    render(<FinalLeaderboard state={state} />);
    expect(screen.getByText(/non-scoring/i)).toBeInTheDocument();
    expect(screen.getByText(state.host.username)).toBeInTheDocument();
  });
});
