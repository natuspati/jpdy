import type { GameLobbyState, GamePromptState } from '@/schemas';

export function findPromptById(
  state: GameLobbyState,
  promptId: number,
): GamePromptState | undefined {
  for (const cat of state.categories) {
    const found = cat.prompts.find((p) => p.prompt_id === promptId);
    if (found) return found;
  }
  return undefined;
}

export function currentPrompt(state: GameLobbyState): GamePromptState | undefined {
  if (state.current_prompt_id === null) return undefined;
  return findPromptById(state, state.current_prompt_id);
}

export function totalConnectedPlayers(state: GameLobbyState): number {
  return state.players.filter(
    (p) => !p.is_banned && p.connection_status === 'connected',
  ).length;
}

export function sortedScoreboard(
  state: GameLobbyState,
): readonly GameLobbyState['players'][number][] {
  return [...state.players].sort((a, b) => b.score - a.score);
}
