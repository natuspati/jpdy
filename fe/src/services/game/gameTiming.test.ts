import { describe, expect, it } from 'vitest';

import {
  ANSWERING_TIME_SECONDS,
  ANSWER_REVEAL_TIME_SECONDS,
  BETTING_ANNOUNCEMENT_SECONDS,
  BETTING_TIME_SECONDS,
  BUZZING_TIME_SECONDS,
  FINAL_ANSWERING_TIME_SECONDS,
  FINAL_BETTING_TIME_SECONDS,
  ROUND_SUMMARY_TIME_SECONDS,
  timerSecondsForPhase,
} from './gameTiming';

describe('timerSecondsForPhase', () => {
  it('uses ten seconds for buzz and keeps other timed phases distinct', () => {
    expect(timerSecondsForPhase('buzz_open')).toBe(BUZZING_TIME_SECONDS);
    expect(BUZZING_TIME_SECONDS).toBe(10);
    expect(timerSecondsForPhase('player_answering')).toBe(ANSWERING_TIME_SECONDS);
    expect(ANSWERING_TIME_SECONDS).toBe(30);
    expect(timerSecondsForPhase('answer_reveal')).toBe(ANSWER_REVEAL_TIME_SECONDS);
    expect(ANSWER_REVEAL_TIME_SECONDS).toBe(30);
    expect(timerSecondsForPhase('round_summary')).toBe(ROUND_SUMMARY_TIME_SECONDS);
    expect(ROUND_SUMMARY_TIME_SECONDS).toBe(10);
  });

  it('times betting rounds and the Final separately', () => {
    expect(timerSecondsForPhase('betting_announcement')).toBe(BETTING_ANNOUNCEMENT_SECONDS);
    expect(timerSecondsForPhase('betting_open')).toBe(BETTING_TIME_SECONDS);
    expect([BETTING_ANNOUNCEMENT_SECONDS, BETTING_TIME_SECONDS]).toEqual([4, 15]);
    expect(timerSecondsForPhase('final_betting')).toBe(FINAL_BETTING_TIME_SECONDS);
    expect(timerSecondsForPhase('final_answering')).toBe(FINAL_ANSWERING_TIME_SECONDS);
    expect([FINAL_BETTING_TIME_SECONDS, FINAL_ANSWERING_TIME_SECONDS]).toEqual([30, 60]);
  });
});
