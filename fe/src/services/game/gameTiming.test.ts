import { describe, expect, it } from 'vitest';

import {
  ANSWERING_TIME_SECONDS,
  ANSWER_REVEAL_TIME_SECONDS,
  BUZZING_TIME_SECONDS,
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
  });
});
