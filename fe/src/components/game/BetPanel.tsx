import { useState } from 'react';

import Button from '@/components/ui/Button';
import Input from '@/components/ui/Input';
import type { GameLobbyState } from '@/schemas';
import { betError } from '@/services/game/phaseGuards';

interface Props {
  state: GameLobbyState;
  categoryName?: string | undefined;
  canBet: boolean;
  onBet: (amount: number) => void;
}

const CheckIcon = () => (
  <svg aria-hidden="true" viewBox="0 0 24 24" className="h-6 w-6 text-emerald-400">
    <path
      d="m5 12 5 5 9-10"
      fill="none"
      stroke="currentColor"
      strokeWidth="3"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

const BetPanel = ({ state, categoryName, canBet, onBet }: Props) => {
  const [draft, setDraft] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState<number | null>(null);
  const placed = state.my_bet ?? submitted;
  const value = draft ?? String(state.min_bet);
  const amount = Number(value);
  const error = value.trim() === '' ? 'Enter a whole number.' : betError(state, amount);

  return (
    <section
      aria-label="Betting"
      className="mx-auto flex w-full max-w-md flex-col items-center gap-3 rounded-xl border border-amber-500/40 bg-slate-900/70 p-4 text-center"
    >
      {categoryName ? <p className="text-sm font-semibold text-amber-300">{categoryName}</p> : null}
      <p className="text-sm text-slate-400">
        {state.min_bet} - {state.max_bet}
      </p>
      {placed !== null ? (
        <p
          aria-label={`Bet placed: ${placed}`}
          className="flex items-center gap-2 text-2xl font-bold tabular-nums text-slate-100"
        >
          <CheckIcon />
          {placed}
        </p>
      ) : canBet ? (
        <form
          className="flex w-full items-start gap-2"
          onSubmit={(event) => {
            event.preventDefault();
            if (error) return;
            setSubmitted(amount);
            onBet(amount);
          }}
        >
          <div className="flex-1 space-y-1 text-left">
            <Input
              type="number"
              aria-label="Your bet"
              min={state.min_bet}
              max={state.max_bet}
              step={1}
              value={value}
              invalid={!!error}
              onChange={(event) => setDraft(event.target.value)}
            />
            {error ? <p className="text-xs text-rose-400">{error}</p> : null}
          </div>
          <Button type="submit" disabled={!!error}>
            Bet
          </Button>
        </form>
      ) : null}
    </section>
  );
};

export default BetPanel;
