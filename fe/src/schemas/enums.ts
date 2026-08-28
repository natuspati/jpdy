import { z } from 'zod';

// Mirrors be/src/enums/lobby.py
export const LobbyStateEnum = z.enum(['created', 'waiting_start', 'in_progress', 'completed']);
export type LobbyStateEnum = z.infer<typeof LobbyStateEnum>;

// Mirrors be/src/enums/game.py
export const GamePhaseEnum = z.enum([
  'waiting_for_players',
  'host_selecting_starting_player',
  'player_selecting_prompt',
  'player_answering',
  'host_judging_answer',
  'buzz_open',
  'finished',
]);
export type GamePhaseEnum = z.infer<typeof GamePhaseEnum>;

export const PlayerConnectionStatusEnum = z.enum(['connected', 'disconnected']);
export type PlayerConnectionStatusEnum = z.infer<typeof PlayerConnectionStatusEnum>;
