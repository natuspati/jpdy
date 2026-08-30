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
});
