import type { GameLobbyState, GamePhaseEnum, GameRoundResult } from '@/schemas';

interface BuildArgs {
  phase?: GamePhaseEnum;
  currentRound?: number;
  totalRounds?: number;
  roundResults?: GameRoundResult[];
  hostId?: number;
  hostName?: string;
  players?: Array<{
    user_id: number;
    username: string;
    score?: number;
    is_banned?: boolean;
    is_selected?: boolean;
    assets_loaded?: boolean;
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
  minBet?: number;
  maxBet?: number;
  currentBet?: number;
  bettingPlayerId?: number | null;
}

export function buildGameState(args: BuildArgs = {}): GameLobbyState {
  const {
    phase = 'waiting_for_players',
    currentRound = 1,
    totalRounds = 1,
    roundResults = [],
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
    minBet = 0,
    maxBet = 0,
    currentBet = 0,
    bettingPlayerId = null,
  } = args;
  return {
    lobby_id: 100,
    state_revision: 0,
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
      assets_loaded: p.assets_loaded ?? false,
    })),
    categories: [
      {
        category_id: 10,
        name: 'Animals',
        kind: 'standard',
        round_number: 1,
        prompts: [
          {
            prompt_id: 101,
            question: 'Q1',
            order: 1,
            is_selected: false,
            score_value: 100,
            is_betting: false,
          },
          {
            prompt_id: 102,
            question: 'Q2',
            order: 2,
            is_selected: false,
            score_value: 200,
            is_betting: false,
          },
        ],
      },
    ],
    phase,
    current_round: currentRound,
    total_rounds: totalRounds,
    round_results: roundResults,
    final_round: null,
    current_prompt_id: currentPromptId,
    selecting_player_id: selectingPlayerId,
    answering_player_id: answeringPlayerId,
    attempted_player_ids: attemptedPlayerIds,
    min_bet: minBet,
    max_bet: maxBet,
    current_bet: currentBet,
    betting_player_id: bettingPlayerId,
    timer_deadline: timerDeadline,
    resolved_prompt_id: resolvedPromptId,
    resolved_answer: resolvedAnswer,
    resolution,
  };
}

export function buildFinalGameState(
  phase: 'final_betting' | 'final_answering' | 'final_reveal' | 'finished' = 'final_betting',
): GameLobbyState {
  const state = buildGameState({
    phase,
    currentRound: 2,
    totalRounds: 2,
    timerDeadline:
      phase === 'final_betting' || phase === 'final_answering'
        ? new Date(Date.now() + 30_000).toISOString()
        : null,
    currentPromptId: phase === 'final_betting' ? null : 201,
    players: [
      { user_id: 2, username: 'alice', score: 500 },
      { user_id: 3, username: 'bob', score: 1000 },
    ],
  });
  state.categories.push({
    category_id: 20,
    name: 'Final topic',
    kind: 'final',
    round_number: 2,
    prompts: [
      {
        prompt_id: 201,
        question: phase === 'final_betting' ? '' : 'The final question',
        question_type: 'text',
        question_media: null,
        answer_media: null,
        order: 1,
        score_value: null,
        is_selected: false,
        is_betting: false,
      },
    ],
  });
  state.final_round = {
    players: state.players.map((player) => ({
      user_id: player.user_id,
      username: player.username,
      score_before_final: player.score,
      decision_submitted: phase !== 'final_betting',
      answer_submitted: phase === 'final_reveal',
      removed: false,
      revealed: phase === 'final_reveal' && player.user_id === 2,
      wager: phase !== 'final_betting' && player.user_id === 2 ? 200 : null,
      answer: phase === 'final_reveal' && player.user_id === 2 ? 'A written response' : null,
      correct: null,
      score_delta: null,
      updated_score: null,
    })),
    current_user_id: phase === 'final_reveal' ? 2 : null,
    is_last_reveal: false,
    skipped_reason: null,
    correct_answer: phase === 'final_reveal' ? 'The correct answer' : null,
    correct_answer_type: phase === 'final_reveal' ? 'text' : null,
    correct_answer_media: null,
  };
  return state;
}
