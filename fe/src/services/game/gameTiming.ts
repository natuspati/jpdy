import type { GamePhaseEnum } from '@/schemas';

export const ANSWERING_TIME_SECONDS = 30;
export const BETTING_ANNOUNCEMENT_SECONDS = 4;
export const BETTING_TIME_SECONDS = 15;
export const BUZZING_TIME_SECONDS = 10;
export const ANSWER_REVEAL_TIME_SECONDS = 30;
export const ROUND_SUMMARY_TIME_SECONDS = 10;
export const FINAL_BETTING_TIME_SECONDS = 30;
export const FINAL_ANSWERING_TIME_SECONDS = 60;

export function timerSecondsForPhase(phase: GamePhaseEnum): number {
  switch (phase) {
    case 'final_betting':
      return FINAL_BETTING_TIME_SECONDS;
    case 'final_answering':
      return FINAL_ANSWERING_TIME_SECONDS;
    case 'betting_announcement':
      return BETTING_ANNOUNCEMENT_SECONDS;
    case 'betting_open':
      return BETTING_TIME_SECONDS;
    case 'buzz_open':
      return BUZZING_TIME_SECONDS;
    case 'answer_reveal':
      return ANSWER_REVEAL_TIME_SECONDS;
    case 'round_summary':
      return ROUND_SUMMARY_TIME_SECONDS;
    default:
      return ANSWERING_TIME_SECONDS;
  }
}
