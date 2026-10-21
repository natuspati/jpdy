import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { buildFinalGameState, buildGameState } from '@/test/fixtures/gameState';
import FinalLeaderboard from './FinalLeaderboard';

describe('FinalLeaderboard', () => {
  it('labels the extra round Final and shows a skipped reason and zero delta', () => {
    const state = buildFinalGameState('finished');
    state.final_round!.skipped_reason = 'all_passed';
    state.round_results = [
      {
        round_number: 2,
        scores: [{ user_id: 2, username: 'alice', score: 500, score_delta: 0, is_banned: false }],
      },
    ];
    render(<FinalLeaderboard state={state} />);
    expect(screen.getByRole('region', { name: 'Final' })).toHaveTextContent('Final topic');
    expect(screen.getByRole('region', { name: 'Final' })).toHaveTextContent('5000');
    expect(screen.getByRole('status')).toHaveTextContent('Final skipped: all passed');
    expect(screen.queryByRole('region', { name: 'Round 2' })).not.toBeInTheDocument();
  });
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

  it('shows the host', () => {
    const state = buildGameState();
    render(<FinalLeaderboard state={state} />);
    expect(screen.queryByText(/non-scoring/i)).not.toBeInTheDocument();
    expect(screen.getByText(state.host.username)).toBeInTheDocument();
  });

  it('uses live roster ordering for banned rows', () => {
    const state = buildGameState({
      players: [
        { user_id: 2, username: 'banned', score: 1_000, is_banned: true },
        { user_id: 3, username: 'active', score: 100 },
      ],
    });
    render(<FinalLeaderboard state={state} />);

    const items = screen.getAllByRole('listitem').map((item) => item.textContent ?? '');
    expect(items[0]).toContain('active');
    expect(items[1]).toContain('banned');
  });

  it('explains an empty completed board', () => {
    const state = buildGameState({ players: [] });
    render(<FinalLeaderboard state={state} />);

    expect(screen.getByText(/no players finished/i)).toBeInTheDocument();
  });

  it('breaks results down per round for multi-round games', () => {
    const state = buildGameState({
      phase: 'finished',
      totalRounds: 2,
      currentRound: 2,
      roundResults: [
        {
          round_number: 1,
          scores: [
            { user_id: 2, username: 'alice', score: 300, score_delta: 300, is_banned: false },
          ],
        },
        {
          round_number: 2,
          scores: [
            { user_id: 2, username: 'alice', score: 500, score_delta: 200, is_banned: false },
          ],
        },
      ],
    });
    state.categories.push({
      category_id: 11,
      name: 'Second round topic',
      kind: 'standard',
      round_number: 2,
      prompts: [],
    });
    render(<FinalLeaderboard state={state} />);

    const roundOne = screen.getByRole('region', { name: 'Round 1' });
    expect(roundOne).toHaveTextContent('Animals');
    expect(roundOne).toHaveTextContent('300+300');
    const roundTwo = screen.getByRole('region', { name: 'Round 2' });
    expect(roundTwo).toHaveTextContent('Second round topic');
    expect(roundTwo).toHaveTextContent('500+200');
  });

  it('shows no round recap for a single-round game', () => {
    render(<FinalLeaderboard state={buildGameState({ phase: 'finished' })} />);

    expect(screen.queryByRole('region', { name: 'Round 1' })).not.toBeInTheDocument();
  });
});
