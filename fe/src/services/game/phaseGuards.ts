import type { GameLobbyState } from '@/schemas';

const isConnectedPlayer = (state: GameLobbyState, userId: number): boolean => {
  const p = state.players.find((pl) => pl.user_id === userId);
  return !!p && !p.is_banned && p.connection_status === 'connected';
};

export const isHost = (state: GameLobbyState, userId: number): boolean =>
  state.host.user_id === userId;

export const canStartGame = (state: GameLobbyState, userId: number): boolean =>
  isHost(state, userId) &&
  state.phase === 'waiting_for_players' &&
  state.players.some((p) => !p.is_banned && p.connection_status === 'connected');

export const canSelectStarter = (state: GameLobbyState, userId: number): boolean =>
  isHost(state, userId) && state.phase === 'host_selecting_starting_player';

export const canSelectPrompt = (
  state: GameLobbyState,
  userId: number,
  promptId: number,
): boolean => {
  if (state.phase !== 'player_selecting_prompt') return false;
  if (state.selecting_player_id !== userId) return false;
  const prompt = state.categories.flatMap((c) => c.prompts).find((p) => p.prompt_id === promptId);
  return !!prompt && !prompt.is_selected;
};

export const canJudge = (state: GameLobbyState, userId: number): boolean =>
  isHost(state, userId) && state.phase === 'player_answering';

export const canAdvanceAnswerReveal = (state: GameLobbyState, userId: number): boolean =>
  isHost(state, userId) && state.phase === 'answer_reveal';

export const canBuzz = (state: GameLobbyState, userId: number): boolean => {
  if (state.phase !== 'buzz_open') return false;
  if (isHost(state, userId)) return false;
  if (state.attempted_player_ids.includes(userId)) return false;
  return isConnectedPlayer(state, userId);
};

export const canBan = (state: GameLobbyState, userId: number): boolean => isHost(state, userId);
