import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { buildGameState } from '@/test/fixtures/gameState';
import BetPanel from './BetPanel';

const betting = (over: Parameters<typeof buildGameState>[0] = {}) =>
  buildGameState({
    phase: 'betting_open',
    currentPromptId: 101,
    selectingPlayerId: 2,
    minBet: 100,
    maxBet: 500,
    ...over,
  });

describe('BetPanel', () => {
  it('lets a bettor submit a bet defaulting above the current one', async () => {
    const onBet = vi.fn();
    const state = betting({ currentBet: 200, bettingPlayerId: 2 });
    render(<BetPanel state={state} categoryName="Animals" canBet onBet={onBet} />);

    expect(screen.getByText('Animals')).toBeInTheDocument();
    expect(screen.getByText('Bet 100 to 500')).toBeInTheDocument();
    expect(screen.getByText('alice: 200')).toBeInTheDocument();
    expect(screen.getByLabelText('Your bet')).toHaveValue(201);

    await userEvent.click(screen.getByRole('button', { name: 'Place bet' }));
    expect(onBet).toHaveBeenCalledWith(201);
  });

  it('blocks invalid bets in the UI', async () => {
    const onBet = vi.fn();
    render(<BetPanel state={betting({ currentBet: 200 })} canBet onBet={onBet} />);
    const input = screen.getByLabelText('Your bet');

    await userEvent.clear(input);
    await userEvent.type(input, '200');

    expect(screen.getByText('Bet more than 200.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Place bet' })).toBeDisabled();
  });

  it('is read-only for other players and the host', () => {
    render(<BetPanel state={betting()} canBet={false} onBet={vi.fn()} />);

    expect(screen.getByText('No bet yet')).toBeInTheDocument();
    expect(screen.queryByLabelText('Your bet')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Place bet' })).not.toBeInTheDocument();
  });
});
