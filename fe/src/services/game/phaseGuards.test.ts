import { describe, expect, it } from 'vitest';

import { buildGameState } from '@/test/fixtures/gameState';
import {
  canBan,
  canBuzz,
  canJudge,
  canSelectPrompt,
  canSelectStarter,
  canStartGame,
  canSubmitAnswer,
  isHost,
} from './phaseGuards';

describe('phaseGuards', () => {
  it('isHost true only for owner', () => {
    const state = buildGameState();
    expect(isHost(state, 1)).toBe(true);
    expect(isHost(state, 2)).toBe(false);
  });

  it('canStartGame requires host, waiting phase, and a connected player', () => {
    const ok = buildGameState({ phase: 'waiting_for_players' });
    expect(canStartGame(ok, 1)).toBe(true);
    expect(canStartGame(ok, 2)).toBe(false);

    const noPlayers = buildGameState({
      phase: 'waiting_for_players',
      players: [{ user_id: 2, username: 'alice', connection_status: 'disconnected' }],
    });
    expect(canStartGame(noPlayers, 1)).toBe(false);
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

  it('canSubmitAnswer requires answerer match and answering phase', () => {
    const ok = buildGameState({ phase: 'player_answering', answeringPlayerId: 2 });
    expect(canSubmitAnswer(ok, 2)).toBe(true);
    expect(canSubmitAnswer(ok, 3)).toBe(false);
  });

  it('canJudge only for host in judging phase', () => {
    const ok = buildGameState({ phase: 'host_judging_answer' });
    expect(canJudge(ok, 1)).toBe(true);
    expect(canJudge(ok, 2)).toBe(false);
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
