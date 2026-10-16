import { describe, expect, it } from 'vitest';

import { buildGameState } from '@/test/fixtures/gameState';
import {
  canAdvanceAnswerReveal,
  canAdvanceRound,
  canBan,
  canBuzz,
  canJudge,
  canSelectPrompt,
  canSelectStarter,
  canStartGame,
  isHost,
} from './phaseGuards';

describe('phaseGuards', () => {
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
});
