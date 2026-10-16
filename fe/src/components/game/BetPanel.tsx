import { useState } from 'react';

import Button from '@/components/ui/Button';
import Input from '@/components/ui/Input';
import { useCountdown } from '@/hooks/useCountdown';
import type { GameLobbyState } from '@/schemas';
import { betError } from '@/services/game/phaseGuards';

interface Props {
  state: GameLobbyState;
  categoryName?: string | undefined;
  canBet: boolean;
  onBet: (amount: number) => void;
}

const BetPanel = ({ state, categoryName, canBet, onBet }: Props) => {
  const seconds = useCountdown(state.timer_deadline);
  const [draft, setDraft] = useState<string | null>(null);
  const holder = state.players.find((p) => p.user_id === state.betting_player_id);
  const value = draft ?? String(Math.max(state.min_bet, state.current_bet + 1));
  const amount = Number(value);
  const error = value.trim() === '' ? 'Enter a whole number.' : betError(state, amount);

  return (
    <section
      aria-label="Betting"
      className="mx-auto flex w-full max-w-md flex-col items-center gap-3 rounded-xl border border-amber-500/40 bg-slate-900/70 p-4 text-center"
    >
      {categoryName ? <p className="text-sm font-semibold text-amber-300">{categoryName}</p> : null}
      <p className="text-slate-300">
        Bet {state.min_bet} to {state.max_bet}
      </p>
      <p className="text-lg font-bold text-slate-100">
        {holder ? `${holder.username}: ${state.current_bet}` : 'No bet yet'}
      </p>
      {seconds !== null ? (
        <p className="text-sm tabular-nums text-slate-400">{seconds}s left</p>
      ) : null}
      {canBet ? (
        <form
          className="flex w-full items-start gap-2"
          onSubmit={(event) => {
            event.preventDefault();
            if (error) return;
            onBet(amount);
            setDraft(null);
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
            Place bet
          </Button>
        </form>
      ) : null}
    </section>
  );
};

export default BetPanel;
