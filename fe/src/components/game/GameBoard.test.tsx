import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { buildGameState } from '@/test/fixtures/gameState';
import GameBoard from './GameBoard';

describe('GameBoard', () => {
  it('disables tiles when the user is not the selector', () => {
    const state = buildGameState({
      phase: 'player_selecting_prompt',
      selectingPlayerId: 2,
    });
    render(<GameBoard state={state} currentUserId={3} onSelect={() => undefined} />);
    const tiles = screen.getAllByRole('button');
    for (const t of tiles) expect(t).toBeDisabled();
  });

  it('emits selected prompt id when selector clicks', async () => {
    const state = buildGameState({
      phase: 'player_selecting_prompt',
      selectingPlayerId: 2,
    });
    const onSelect = vi.fn();
    render(<GameBoard state={state} currentUserId={2} onSelect={onSelect} />);
    const tiles = screen.getAllByRole('button');
    await userEvent.click(tiles[0]);
    expect(onSelect).toHaveBeenCalledWith(101);
  });

  it('renders an em-dash for spent tiles', () => {
    const state = buildGameState({ phase: 'player_selecting_prompt', selectingPlayerId: 2 });
    state.categories[0].prompts[0].is_selected = true;
    render(<GameBoard state={state} currentUserId={2} onSelect={() => undefined} />);
    expect(screen.getByRole('button', { name: '—' })).toBeInTheDocument();
  });
});
