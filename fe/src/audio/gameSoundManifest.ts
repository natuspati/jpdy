import answerReveal from '@/assets/game-audio/answer-reveal.mp3';
import answeringLoop from '@/assets/game-audio/answering-loop.mp3';
import boardLoop from '@/assets/game-audio/board-loop.mp3';
import buzz from '@/assets/game-audio/buzz.mp3';
import clueSelected from '@/assets/game-audio/clue-selected.mp3';
import correct from '@/assets/game-audio/correct.mp3';
import gameComplete from '@/assets/game-audio/game-complete.mp3';
import intro from '@/assets/game-audio/intro.mp3';
import timeExpired from '@/assets/game-audio/time-expired.mp3';
import wrong from '@/assets/game-audio/wrong.mp3';

export const gameSoundManifest = {
  intro,
  boardLoop,
  answeringLoop,
  clueSelected,
  buzz,
  correct,
  wrong,
  timeExpired,
  answerReveal,
  gameComplete,
} as const;

export type GameSoundName = keyof typeof gameSoundManifest;
