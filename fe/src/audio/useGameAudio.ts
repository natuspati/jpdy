import { useContext } from 'react';

import { GameAudioContext, type GameAudioContextValue } from './gameAudioContext';

export function useGameAudio(): GameAudioContextValue {
  const context = useContext(GameAudioContext);
  if (!context) throw new Error('useGameAudio must be used inside GameAudioProvider');
  return context;
}
