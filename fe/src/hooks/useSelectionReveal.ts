import { useEffect, useLayoutEffect, useRef, useState } from 'react';

import type { GameLobbyState } from '@/schemas';

export const SELECTION_REVEAL_MS = 1000;

const isOpening = (phase: GameLobbyState['phase'] | undefined): boolean =>
  phase === 'player_answering' || phase === 'betting_announcement';

/**
 * Id of the prompt that was just picked, for the first second after the selection arrives.
 * Everyone keeps seeing the board with that tile flashing before the clue opens. Only a live
 * pick (selecting -> answering or betting) triggers it, so a reconnect straight into a clue skips the pause.
 */
export const useSelectionReveal = (state: GameLobbyState | null): number | null => {
  const phase = state?.phase;
  const promptId = state?.current_prompt_id ?? null;
  const [revealing, setRevealing] = useState<number | null>(null);
  const previousPhase = useRef(phase);

  // Layout effect: the reveal flag is set before paint, so the clue never flashes up first.
  useLayoutEffect(() => {
    if (isOpening(phase) && previousPhase.current === 'player_selecting_prompt') {
      setRevealing(promptId);
    }
    previousPhase.current = phase;
  }, [phase, promptId]);

  useEffect(() => {
    if (revealing === null) return;
    const timer = setTimeout(() => setRevealing(null), SELECTION_REVEAL_MS);
    return () => clearTimeout(timer);
  }, [revealing]);

  return isOpening(phase) && revealing === promptId ? revealing : null;
};
