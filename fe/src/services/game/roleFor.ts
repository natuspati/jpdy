import type { GameLobbyState } from '@/schemas';

export type Role = 'host' | 'selector' | 'answerer' | 'buzzer' | 'spectator' | 'banned';

/**
 * Pure mapping from (state, userId) to the user's current functional role.
 * Used by the page to pick which sub-view to render.
 *
 * - 'host': lobby owner; runs control panel and judges.
 * - 'selector': player whose turn it is to pick a prompt.
 * - 'answerer': player who must submit an answer right now.
 * - 'buzzer': eligible player during BUZZ_OPEN (connected, not banned, not
 *   yet attempted, not host).
 * - 'banned': has been banned by the host.
 * - 'spectator': everyone else (waiting for someone else's move).
 */
export function roleFor(state: GameLobbyState, userId: number): Role {
  if (state.host.user_id === userId) return 'host';
  const player = state.players.find((p) => p.user_id === userId);
  if (player?.is_banned) return 'banned';
  if (state.answering_player_id === userId) return 'answerer';
  if (
    state.phase === 'buzz_open' &&
    player &&
    !player.is_banned &&
    player.connection_status === 'connected' &&
    !state.attempted_player_ids.includes(userId)
  ) {
    return 'buzzer';
  }
  if (state.phase === 'player_selecting_prompt' && state.selecting_player_id === userId) {
    return 'selector';
  }
  return 'spectator';
}
