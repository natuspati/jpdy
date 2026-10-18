import { describe, expect, it } from 'vitest';

import { buildFinalGameState, buildGameState } from '@/test/fixtures/gameState';
import {
  canAdvanceAnswerReveal,
  canAdvanceRound,
  canBan,
  canBuzz,
  betError,
  canJudge,
  canPlaceBet,
  canSelectPrompt,
  canSelectStarter,
  canStartGame,
  canSubmitFinalAnswer,
  canSubmitFinalWager,
  canJudgeFinalAnswer,
  canAdvanceFinalReveal,
  isHost,
} from './phaseGuards';

describe('phaseGuards', () => {
  it('gates immutable Final decisions by phase, saved eligibility, deadline and host role', () => {
    const state = buildFinalGameState();
    expect(canSubmitFinalWager(state, 2)).toBe(true);
    expect(canSubmitFinalWager(state, 1)).toBe(false);
    expect(canSubmitFinalWager(state, 99)).toBe(false);
    state.final_round!.players[0].decision_submitted = true;
    expect(canSubmitFinalWager(state, 2)).toBe(false);
    const answering = buildFinalGameState('final_answering');
    expect(canSubmitFinalAnswer(answering, 2)).toBe(true);
    expect(canSubmitFinalAnswer(answering, 3)).toBe(false);
    answering.final_round!.players[0].removed = true;
    expect(canSubmitFinalAnswer(answering, 2)).toBe(false);
    answering.final_round!.players[0].removed = false;
    answering.timer_deadline = new Date(Date.now()).toISOString();
    expect(canSubmitFinalAnswer(answering, 2)).toBe(false);
  });

  it('requires judgment before Final advance and never offers normal actions for Final prompts', () => {
    const state = buildFinalGameState('final_reveal');
    expect(canJudgeFinalAnswer(state, 1)).toBe(true);
    expect(canJudgeFinalAnswer(state, 2)).toBe(false);
    expect(canAdvanceFinalReveal(state, 1)).toBe(false);
    state.final_round!.players[0].correct = false;
    expect(canJudgeFinalAnswer(state, 1)).toBe(false);
    expect(canAdvanceFinalReveal(state, 1)).toBe(true);
    state.phase = 'player_selecting_prompt';
    state.selecting_player_id = 2;
    expect(canSelectPrompt(state, 2, 201)).toBe(false);
  });
  it('isHost true only for owner', () => {
    const state = buildGameState();
    expect(isHost(state, 1)).toBe(true);
    expect(isHost(state, 2)).toBe(false);
  });

  it('canStartGame requires host, waiting phase, and loaded connected players unless forced', () => {
    const ok = buildGameState({
      phase: 'waiting_for_players',
      players: [
        { user_id: 2, username: 'alice', assets_loaded: true },
        { user_id: 3, username: 'bob', assets_loaded: true },
      ],
    });
    expect(canStartGame(ok, 1)).toBe(true);
    expect(canStartGame(ok, 2)).toBe(false);

    const loading = buildGameState({ phase: 'waiting_for_players' });
    expect(canStartGame(loading, 1)).toBe(false);
    expect(canStartGame(loading, 1, true)).toBe(true);
    expect(canStartGame(loading, 2, true)).toBe(false);

    const noPlayers = buildGameState({
      phase: 'waiting_for_players',
      players: [{ user_id: 2, username: 'alice', connection_status: 'disconnected' }],
    });
    expect(canStartGame(noPlayers, 1)).toBe(false);
    expect(canStartGame(noPlayers, 1, true)).toBe(false);
  });

  it('canSelectStarter only for host during host_selecting_starting_player', () => {
    const ok = buildGameState({ phase: 'host_selecting_starting_player' });
    expect(canSelectStarter(ok, 1)).toBe(true);
    expect(canSelectStarter(ok, 2)).toBe(false);
  });

  it('canSelectPrompt requires selector and an unselected prompt', () => {
    const ok = buildGameState({
      phase: 'player_selecting_prompt',
      selectingPlayerId: 2,
    });
    expect(canSelectPrompt(ok, 2, 101)).toBe(true);
    expect(canSelectPrompt(ok, 3, 101)).toBe(false);
    expect(canSelectPrompt(ok, 2, 999)).toBe(false);
  });

  it('canSelectPrompt rejects prompts that belong to another round', () => {
    const state = buildGameState({
      phase: 'player_selecting_prompt',
      selectingPlayerId: 2,
      currentRound: 2,
      totalRounds: 2,
    });
    expect(canSelectPrompt(state, 2, 101)).toBe(false);
    state.categories[0].round_number = 2;
    expect(canSelectPrompt(state, 2, 101)).toBe(true);
  });

  it('canAdvanceRound only for host during round_summary', () => {
    const summary = buildGameState({ phase: 'round_summary', totalRounds: 2 });
    expect(canAdvanceRound(summary, 1)).toBe(true);
    expect(canAdvanceRound(summary, 2)).toBe(false);
    expect(canAdvanceRound(buildGameState({ phase: 'answer_reveal' }), 1)).toBe(false);
  });

  it('canJudge only for host while a player is answering', () => {
    const ok = buildGameState({ phase: 'player_answering', answeringPlayerId: 2 });
    expect(canJudge(ok, 1)).toBe(true);
    expect(canJudge(ok, 2)).toBe(false);
  });

  it('canAdvanceAnswerReveal only for host during answer reveal', () => {
    const ok = buildGameState({
      phase: 'answer_reveal',
      currentPromptId: 101,
      resolvedPromptId: 101,
      resolvedAnswer: 'Q1 answer',
      resolution: 'correct',
    });
    expect(canAdvanceAnswerReveal(ok, 1)).toBe(true);
    expect(canAdvanceAnswerReveal(ok, 2)).toBe(false);
  });

  it('canBuzz: only eligible, non-host, non-attempted in buzz_open', () => {
    const ok = buildGameState({ phase: 'buzz_open', attemptedPlayerIds: [3] });
    expect(canBuzz(ok, 2)).toBe(true);
    expect(canBuzz(ok, 3)).toBe(false);
    expect(canBuzz(ok, 1)).toBe(false);
  });

  it('canBan only for host', () => {
    const state = buildGameState();
    expect(canBan(state, 1)).toBe(true);
    expect(canBan(state, 2)).toBe(false);
  });

  it('canPlaceBet lets only the selector bet first, then everyone but the selector', () => {
    const first = buildGameState({ phase: 'player_betting', selectingPlayerId: 2 });
    expect(canPlaceBet(first, 2)).toBe(true);
    expect(canPlaceBet(first, 3)).toBe(false);
    expect(canPlaceBet(first, 1)).toBe(false);

    const open = buildGameState({ phase: 'betting_open', selectingPlayerId: 2 });
    expect(canPlaceBet(open, 2)).toBe(false);
    expect(canPlaceBet(open, 3)).toBe(true);
    expect(canPlaceBet(open, 1)).toBe(false);

    const banned = buildGameState({
      phase: 'betting_open',
      selectingPlayerId: 2,
      players: [
        { user_id: 2, username: 'alice' },
        { user_id: 3, username: 'bob', is_banned: true },
      ],
    });
    expect(canPlaceBet(banned, 3)).toBe(false);
    expect(canPlaceBet(buildGameState({ phase: 'buzz_open' }), 3)).toBe(false);
  });

  it('betError checks range, whole numbers and strictly higher bets', () => {
    const state = buildGameState({
      phase: 'betting_open',
      minBet: 100,
      maxBet: 500,
      currentBet: 200,
    });
    expect(betError(state, 50)).toMatch(/between 100 and 500/);
    expect(betError(state, 501)).toMatch(/between 100 and 500/);
    expect(betError(state, 200)).toBe('Bet more than 200.');
    expect(betError(state, 250.5)).toBe('Enter a whole number.');
    expect(betError(state, Number.NaN)).toBe('Enter a whole number.');
    expect(betError(state, 201)).toBeNull();
    expect(betError(state, 500)).toBeNull();
  });
});
