import { fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { buildGameState } from '@/test/fixtures/gameState';
import RoundSummary from './RoundSummary';

const summaryState = () =>
  buildGameState({
    phase: 'round_summary',
    totalRounds: 2,
    timerDeadline: '2026-01-01T00:00:07Z',
    roundResults: [
      {
        round_number: 1,
        scores: [
          { user_id: 2, username: 'alice', score: 300, score_delta: 300, is_banned: false },
          { user_id: 3, username: 'bob', score: -100, score_delta: -100, is_banned: false },
        ],
      },
    ],
  });

describe('RoundSummary', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-01-01T00:00:00Z'));
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it('lists ranked standings with cumulative score and round delta, plus the countdown', () => {
    render(<RoundSummary state={summaryState()} currentUserId={2} onAdvance={vi.fn()} />);

    expect(screen.getByRole('heading', { name: 'Round 1 complete' })).toBeInTheDocument();
    const rows = screen.getAllByRole('listitem').map((li) => li.textContent ?? '');
    expect(rows[0]).toContain('1.alice300+300');
    expect(rows[1]).toContain('2.bob-100-100');
    expect(screen.getByText('7s')).toBeInTheDocument();
  });

  it('lets the host start the next round', () => {
    const onAdvance = vi.fn();
    render(<RoundSummary state={summaryState()} currentUserId={1} onAdvance={onAdvance} />);

    fireEvent.click(screen.getByRole('button', { name: 'Start round 2' }));

    expect(onAdvance).toHaveBeenCalledTimes(1);
  });

  it('tells players the next round starts automatically', () => {
    render(<RoundSummary state={summaryState()} currentUserId={2} onAdvance={vi.fn()} />);

    expect(screen.queryByRole('button')).not.toBeInTheDocument();
    expect(screen.getByText('Next round starts automatically')).toBeInTheDocument();
  });
});
