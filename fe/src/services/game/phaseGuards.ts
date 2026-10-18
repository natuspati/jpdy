import type { GameLobbyState } from '@/schemas';

const isConnectedPlayer = (state: GameLobbyState, userId: number): boolean => {
  const p = state.players.find((pl) => pl.user_id === userId);
  return !!p && !p.is_banned && p.connection_status === 'connected';
};

export const isHost = (state: GameLobbyState, userId: number): boolean =>
  state.host.user_id === userId;

const eligiblePlayers = (state: GameLobbyState): GameLobbyState['players'] =>
  state.players.filter((p) => !p.is_banned && p.connection_status === 'connected');

export const playersStillLoading = (state: GameLobbyState): number =>
  eligiblePlayers(state).filter((p) => !p.assets_loaded).length;

// `force` is the host override that ignores players who have not finished loading.
export const canStartGame = (state: GameLobbyState, userId: number, force = false): boolean =>
  isHost(state, userId) &&
  state.phase === 'waiting_for_players' &&
  eligiblePlayers(state).length > 0 &&
  (force || playersStillLoading(state) === 0);

export const canSelectStarter = (state: GameLobbyState, userId: number): boolean =>
  isHost(state, userId) && state.phase === 'host_selecting_starting_player';

export const canSelectPrompt = (
  state: GameLobbyState,
  userId: number,
  promptId: number,
): boolean => {
  if (state.phase !== 'player_selecting_prompt') return false;
  if (state.selecting_player_id !== userId) return false;
  const category = state.categories.find((c) => c.prompts.some((p) => p.prompt_id === promptId));
  if (!category || category.kind === 'final' || category.round_number !== state.current_round)
    return false;
  const prompt = category.prompts.find((p) => p.prompt_id === promptId);
  return !!prompt && !prompt.is_selected;
};

export const canJudge = (state: GameLobbyState, userId: number): boolean =>
  isHost(state, userId) && state.phase === 'player_answering';

export const canAdvanceAnswerReveal = (state: GameLobbyState, userId: number): boolean =>
  isHost(state, userId) && state.phase === 'answer_reveal';

export const canAdvanceRound = (state: GameLobbyState, userId: number): boolean =>
  isHost(state, userId) && state.phase === 'round_summary';

export const canPlaceBet = (state: GameLobbyState, userId: number): boolean => {
  if (!isConnectedPlayer(state, userId)) return false;
  const isSelector = state.selecting_player_id === userId;
  if (state.phase === 'player_betting') return isSelector;
  return state.phase === 'betting_open' && !isSelector;
};

// UX-only validation; the server stays authoritative.
export const betError = (state: GameLobbyState, amount: number): string | null => {
  if (!Number.isInteger(amount)) return 'Enter a whole number.';
  if (amount < state.min_bet || amount > state.max_bet) {
    return `Bet between ${state.min_bet} and ${state.max_bet}.`;
  }
  if (amount <= state.current_bet) return `Bet more than ${state.current_bet}.`;
  return null;
};

export const canBuzz = (state: GameLobbyState, userId: number): boolean => {
  if (state.phase !== 'buzz_open') return false;
  if (isHost(state, userId)) return false;
  if (state.attempted_player_ids.includes(userId)) return false;
  return isConnectedPlayer(state, userId);
};

export const canBan = (state: GameLobbyState, userId: number): boolean => isHost(state, userId);

export const isFinalPhase = (phase: GameLobbyState['phase']): boolean =>
  phase === 'final_betting' || phase === 'final_answering' || phase === 'final_reveal';

const finalPlayer = (state: GameLobbyState, userId: number) =>
  state.final_round?.players.find((player) => player.user_id === userId && !player.removed);

const beforeDeadline = (state: GameLobbyState): boolean =>
  state.timer_deadline !== null && Date.now() < Date.parse(state.timer_deadline);

export const canSubmitFinalWager = (state: GameLobbyState, userId: number): boolean => {
  const player = finalPlayer(state, userId);
  return (
    state.phase === 'final_betting' &&
    !isHost(state, userId) &&
    isConnectedPlayer(state, userId) &&
    beforeDeadline(state) &&
    !!player &&
    !player.decision_submitted
  );
};

export const canSubmitFinalAnswer = (state: GameLobbyState, userId: number): boolean => {
  const player = finalPlayer(state, userId);
  return (
    state.phase === 'final_answering' &&
    !isHost(state, userId) &&
    isConnectedPlayer(state, userId) &&
    beforeDeadline(state) &&
    !!player &&
    player.wager !== null &&
    !player.answer_submitted
  );
};

export const canJudgeFinalAnswer = (state: GameLobbyState, userId: number): boolean => {
  const player = finalPlayer(state, state.final_round?.current_user_id ?? -1);
  return (
    state.phase === 'final_reveal' &&
    isHost(state, userId) &&
    !!player?.revealed &&
    player.correct === null &&
    !!player.answer?.trim()
  );
};

export const canAdvanceFinalReveal = (state: GameLobbyState, userId: number): boolean => {
  const player = finalPlayer(state, state.final_round?.current_user_id ?? -1);
  return (
    state.phase === 'final_reveal' &&
    isHost(state, userId) &&
    !!player?.revealed &&
    player.correct !== null
  );
};
