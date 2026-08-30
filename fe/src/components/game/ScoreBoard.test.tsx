import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { buildGameState } from '@/test/fixtures/gameState';
import ScoreBoard from './ScoreBoard';

describe('ScoreBoard', () => {
  it('renders host first and players as score tiles with active highlights', () => {
    const state = buildGameState({
      phase: 'player_answering',
      answeringPlayerId: 2,
    });
    render(<ScoreBoard state={state} currentUserId={3} />);

    const items = screen.getAllByRole('listitem').map((item) => item.textContent ?? '');
    expect(items[0]).toContain(state.host.username);
    expect(screen.getByTestId('host-player-tile')).toHaveAttribute('data-active', 'true');
    expect(screen.getByTestId('player-tile-2')).toHaveAttribute('data-active', 'true');
    expect(screen.getByTestId('player-tile-2')).toHaveTextContent('alice0');
  });

  it('highlights the selected clue picker without status labels', () => {
    const state = buildGameState({
      phase: 'player_selecting_prompt',
      selectingPlayerId: 2,
    });
    render(<ScoreBoard state={state} currentUserId={3} />);

    expect(screen.getByTestId('player-tile-2')).toHaveAttribute('data-active', 'true');
    expect(screen.queryByText('SELECTING')).not.toBeInTheDocument();
  });

  it('keeps banned player tiles last and lets the host ban or unban with stop-sign actions', async () => {
    const onBan = vi.fn();
    const onUnban = vi.fn();
    const state = buildGameState({
      players: [
        { user_id: 2, username: 'banned', score: 1_000, is_banned: true },
        { user_id: 3, username: 'active', score: 100 },
      ],
    });
    render(
      <ScoreBoard
        state={state}
        currentUserId={state.host.user_id}
        onBan={onBan}
        onUnban={onUnban}
      />,
    );

    const items = screen.getAllByRole('listitem').map((item) => item.textContent ?? '');
    expect(items[1]).toContain('active');
    expect(items[2]).toContain('banned');
    expect(screen.getByTestId('player-tile-2')).toHaveAttribute('data-muted', 'true');
    await userEvent.click(screen.getByRole('button', { name: 'Unban banned' }));
    await userEvent.click(screen.getByRole('button', { name: 'Ban active' }));
    expect(onUnban).toHaveBeenCalledWith(2);
    expect(onBan).toHaveBeenCalledWith(3);
  });

  it('shows a non-clickable muted banned state to non-host players', () => {
    const state = buildGameState({
      players: [
        { user_id: 2, username: 'banned', score: 100, is_banned: true },
        { user_id: 3, username: 'active', score: 50, connection_status: 'disconnected' },
      ],
    });
    render(<ScoreBoard state={state} currentUserId={3} />);

    expect(screen.getByText('banned')).toBeInTheDocument();
    expect(screen.getByLabelText('Banned')).toBeInTheDocument();
    expect(screen.getByTestId('player-tile-2')).toHaveAttribute('data-muted', 'true');
    expect(screen.getByTestId('player-tile-3')).toHaveAttribute('data-muted', 'true');
    expect(screen.queryByRole('button', { name: /ban|unban/i })).not.toBeInTheDocument();
  });
});
