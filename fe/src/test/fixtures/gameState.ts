import type { GameLobbyState, GamePhaseEnum } from '@/schemas';

interface BuildArgs {
  phase?: GamePhaseEnum;
  hostId?: number;
  hostName?: string;
  players?: Array<{
    user_id: number;
    username: string;
    score?: number;
    is_banned?: boolean;
    is_selected?: boolean;
    connection_status?: 'connected' | 'disconnected';
  }>;
  selectingPlayerId?: number | null;
  answeringPlayerId?: number | null;
  attemptedPlayerIds?: number[];
  currentPromptId?: number | null;
  timerDeadline?: string | null;
  resolvedPromptId?: number | null;
  resolvedAnswer?: string | null;
  resolution?: 'correct' | 'unanswered' | 'expired' | null;
}

export function buildGameState(args: BuildArgs = {}): GameLobbyState {
  const {
    phase = 'waiting_for_players',
    hostId = 1,
    hostName = 'hosty',
    players = [
      { user_id: 2, username: 'alice' },
      { user_id: 3, username: 'bob' },
    ],
    selectingPlayerId = null,
    answeringPlayerId = null,
    attemptedPlayerIds = [],
    currentPromptId = null,
    timerDeadline = null,
    resolvedPromptId = null,
    resolvedAnswer = null,
    resolution = null,
  } = args;
  return {
    lobby_id: 100,
    host: {
      user_id: hostId,
      username: hostName,
      connection_status: 'connected',
    },
    players: players.map((p) => ({
      user_id: p.user_id,
      username: p.username,
      score: p.score ?? 0,
      connection_status: p.connection_status ?? 'connected',
      is_selected: p.is_selected ?? false,
      is_banned: p.is_banned ?? false,
    })),
    categories: [
      {
        category_id: 10,
        name: 'Animals',
        prompts: [
          { prompt_id: 101, question: 'Q1', order: 1, is_selected: false, score_value: 100 },
          { prompt_id: 102, question: 'Q2', order: 2, is_selected: false, score_value: 200 },
        ],
      },
    ],
    phase,
    current_prompt_id: currentPromptId,
    selecting_player_id: selectingPlayerId,
    answering_player_id: answeringPlayerId,
    attempted_player_ids: attemptedPlayerIds,
    timer_deadline: timerDeadline,
    resolved_prompt_id: resolvedPromptId,
    resolved_answer: resolvedAnswer,
    resolution,
  };
}
