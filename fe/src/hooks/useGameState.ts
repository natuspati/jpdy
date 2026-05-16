import { useMemo } from 'react';

import { currentPrompt, sortedScoreboard } from '@/services/game/gameDerivations';
import { roleFor, type Role } from '@/services/game/roleFor';
import type { GameLobbyState, GamePlayerState, GamePromptState } from '@/schemas';

interface UseGameStateResult {
  role: Role;
  currentPrompt: GamePromptState | undefined;
  scoreboard: readonly GamePlayerState[];
  remainingDeadline: string | null;
}

export function useGameStateView(state: GameLobbyState, userId: number): UseGameStateResult {
  return useMemo(
    () => ({
      role: roleFor(state, userId),
      currentPrompt: currentPrompt(state),
      scoreboard: sortedScoreboard(state),
      remainingDeadline: state.timer_deadline,
    }),
    [state, userId],
  );
}
