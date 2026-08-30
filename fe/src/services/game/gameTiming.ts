import type { GamePhaseEnum } from '@/schemas';

export const ANSWERING_TIME_SECONDS = 30;
export const BUZZING_TIME_SECONDS = 10;
export const ANSWER_REVEAL_TIME_SECONDS = 5;

export function timerSecondsForPhase(phase: GamePhaseEnum): number {
  switch (phase) {
    case 'buzz_open':
      return BUZZING_TIME_SECONDS;
    case 'answer_reveal':
      return ANSWER_REVEAL_TIME_SECONDS;
    default:
      return ANSWERING_TIME_SECONDS;
  }
}
