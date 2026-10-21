import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { buildGameState } from '@/test/fixtures/gameState';
import BetPanel from './BetPanel';

const betting = (over: Parameters<typeof buildGameState>[0] = {}) =>
  buildGameState({
    phase: 'betting_open',
    currentPromptId: 101,
    minBet: 100,
    maxBet: 500,
    ...over,
  });

describe('BetPanel', () => {
  it('prefills the minimum bet and submits it once', async () => {
    const onBet = vi.fn();
    render(<BetPanel state={betting()} categoryName="Animals" canBet onBet={onBet} />);

    expect(screen.getByText('Animals')).toBeInTheDocument();
    expect(screen.getByText('100 - 500')).toBeInTheDocument();
    expect(screen.getByLabelText('Your bet')).toHaveValue(100);

    const input = screen.getByLabelText('Your bet');
    await userEvent.clear(input);
    await userEvent.type(input, '350');
    await userEvent.click(screen.getByRole('button', { name: 'Bet' }));

    expect(onBet).toHaveBeenCalledExactlyOnceWith(350);
    expect(screen.queryByLabelText('Your bet')).not.toBeInTheDocument();
    expect(screen.getByLabelText('Bet placed: 350')).toBeInTheDocument();
  });

  it('shows the locked bet from the server after a reload', () => {
    render(<BetPanel state={betting({ myBet: 250 })} canBet={false} onBet={vi.fn()} />);

    expect(screen.getByLabelText('Bet placed: 250')).toBeInTheDocument();
    expect(screen.queryByLabelText('Your bet')).not.toBeInTheDocument();
  });

  it('blocks out-of-range bets in the UI', async () => {
    const onBet = vi.fn();
    render(<BetPanel state={betting()} canBet onBet={onBet} />);
    const input = screen.getByLabelText('Your bet');

    await userEvent.clear(input);
    await userEvent.type(input, '501');

    expect(screen.getByText('Bet between 100 and 500.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Bet' })).toBeDisabled();
  });

  it('has no input for the host or other non-bettors', () => {
    render(<BetPanel state={betting()} canBet={false} onBet={vi.fn()} />);

    expect(screen.queryByLabelText('Your bet')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Bet' })).not.toBeInTheDocument();
  });
});
