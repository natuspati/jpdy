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

  it('gives short and long category titles equal header regions', () => {
    const state = buildGameState({ phase: 'player_selecting_prompt', selectingPlayerId: 2 });
    state.categories.push({
      category_id: 11,
      name: 'A category title long enough to wrap onto another line',
      kind: 'standard',
      round_number: 1,
      prompts: [
        {
          prompt_id: 103,
          question: 'Q3',
          order: 1,
          is_selected: false,
          score_value: 100,
          is_betting: false,
        },
        {
          prompt_id: 104,
          question: 'Q4',
          order: 2,
          is_selected: false,
          score_value: 200,
          is_betting: false,
        },
      ],
    });

    const { container } = render(
      <GameBoard state={state} currentUserId={2} onSelect={() => undefined} />,
    );

    expect(container.querySelectorAll('.line-clamp-2')).toHaveLength(2);
    expect(screen.getByText(/long enough/i)).toHaveClass('line-clamp-2');
  });

  it('flashes the just-picked tile with its value instead of an em-dash', () => {
    const state = buildGameState({ phase: 'player_answering', selectingPlayerId: 2 });
    state.categories[0].prompts[0].is_selected = true;
    render(
      <GameBoard state={state} currentUserId={2} onSelect={() => undefined} flashPromptId={101} />,
    );
    const tile = screen.getByRole('button', { name: '100' });
    expect(tile).toHaveClass('animate-prompt-flash');
    expect(tile).toBeDisabled();
  });

  it('shows only the current round while keeping other rounds in state', () => {
    const state = buildGameState({
      phase: 'player_selecting_prompt',
      selectingPlayerId: 2,
      currentRound: 2,
      totalRounds: 2,
    });
    state.categories[0].prompts.forEach((prompt) => {
      prompt.is_selected = true;
    });
    state.categories.push({
      category_id: 11,
      name: 'Round two category',
      kind: 'standard',
      round_number: 2,
      prompts: [
        {
          prompt_id: 103,
          question: 'Q3',
          order: 1,
          is_selected: false,
          score_value: 200,
          is_betting: false,
        },
        {
          prompt_id: 104,
          question: 'Q4',
          order: 2,
          is_selected: false,
          score_value: 400,
          is_betting: false,
        },
      ],
    });

    const { container } = render(
      <GameBoard state={state} currentUserId={2} onSelect={() => undefined} />,
    );

    expect(screen.getByText('Round two category')).toBeInTheDocument();
    expect(screen.queryByText('Animals')).not.toBeInTheDocument();
    expect(container.querySelectorAll('.line-clamp-2')).toHaveLength(1);
    expect(container.firstElementChild).toHaveClass('grid-cols-1');
    expect(screen.getByRole('button', { name: '200' })).toBeEnabled();
    expect(screen.getByRole('button', { name: '400' })).toBeEnabled();
  });
});
