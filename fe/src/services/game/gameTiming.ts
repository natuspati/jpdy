import type { GamePhaseEnum } from '@/schemas';

export const ANSWERING_TIME_SECONDS = 30;
export const BETTING_TIME_SECONDS = 10;
export const BUZZING_TIME_SECONDS = 10;
export const ANSWER_REVEAL_TIME_SECONDS = 30;
export const ROUND_SUMMARY_TIME_SECONDS = 10;
export const FINAL_SUBMISSION_TIME_SECONDS = 30;

export function timerSecondsForPhase(phase: GamePhaseEnum): number {
  switch (phase) {
    case 'final_betting':
    case 'final_answering':
      return FINAL_SUBMISSION_TIME_SECONDS;
    case 'player_betting':
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
