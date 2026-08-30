import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { buildGameState } from '@/test/fixtures/gameState';
import ScoreBoard from './ScoreBoard';

describe('ScoreBoard', () => {
  it('labels the active answerer and host action', () => {
    const state = buildGameState({
      phase: 'player_answering',
      answeringPlayerId: 2,
    });
    render(<ScoreBoard state={state} currentUserId={3} />);

    expect(screen.getByText('ANSWERING')).toBeInTheDocument();
    expect(screen.getByText('HOST ACTION')).toBeInTheDocument();
  });

  it('labels the current clue selector', () => {
    const state = buildGameState({
      phase: 'player_selecting_prompt',
      selectingPlayerId: 2,
    });
    render(<ScoreBoard state={state} currentUserId={3} />);

    expect(screen.getByText('SELECTING')).toBeInTheDocument();
  });

  it('keeps banned rows last for host and exposes unban control', () => {
    const state = buildGameState({
      players: [
        { user_id: 2, username: 'banned', score: 1_000, is_banned: true },
        { user_id: 3, username: 'active', score: 100 },
      ],
    });
    render(<ScoreBoard state={state} currentUserId={state.host.user_id} />);

    const items = screen.getAllByRole('listitem').map((item) => item.textContent ?? '');
    expect(items[1]).toContain('active');
    expect(items[2]).toContain('banned');
    expect(screen.getByRole('button', { name: 'unban' })).toBeInTheDocument();
  });

  it('does not render banned players or moderation controls in player-visible state', () => {
    const state = buildGameState({
      players: [{ user_id: 3, username: 'active', score: 100 }],
    });
    render(<ScoreBoard state={state} currentUserId={3} />);

    expect(screen.queryByText('banned')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /ban|unban/i })).not.toBeInTheDocument();
  });
});
