import { createContext } from 'react';

import type { GameLobbyState, GameSoundCuePayload } from '@/schemas';

export interface GameAudioContextValue {
  enabled: boolean;
  volume: number;
  blockedMessage: string | null;
  enableSound: () => Promise<void>;
  toggleMuted: () => void;
  setVolume: (value: number) => void;
  syncGameState: (state: GameLobbyState | null) => void;
  playCue: (cue: GameSoundCuePayload) => void;
  stopAll: () => void;
}

export const GameAudioContext = createContext<GameAudioContextValue | null>(null);
