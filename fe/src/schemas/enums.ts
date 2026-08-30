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
  'buzz_open',
  'answer_reveal',
  'finished',
]);
export type GamePhaseEnum = z.infer<typeof GamePhaseEnum>;

export const GameResolutionEnum = z.enum(['correct', 'unanswered', 'expired']);
export type GameResolutionEnum = z.infer<typeof GameResolutionEnum>;

export const PlayerConnectionStatusEnum = z.enum(['connected', 'disconnected']);
export type PlayerConnectionStatusEnum = z.infer<typeof PlayerConnectionStatusEnum>;
