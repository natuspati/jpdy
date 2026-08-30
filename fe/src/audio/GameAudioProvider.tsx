import { type ReactNode, useCallback, useEffect, useMemo, useRef, useState } from 'react';

import type { GameLobbyState, GameSoundCuePayload } from '@/schemas';
import { GameAudioContext, type GameAudioContextValue } from './gameAudioContext';
import { gameSoundManifest, type GameSoundName } from './gameSoundManifest';

const STORAGE_KEY = 'jpdy.game-audio-preferences';
const BACKGROUND_GAIN = 0.1;
const EFFECT_GAIN = 0.2;

type BackgroundTrack = 'boardLoop' | 'answeringLoop' | null;

interface StoredAudioPreferences {
  enabled: boolean;
  volume: number;
}

function readPreferences(): StoredAudioPreferences {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return { enabled: false, volume: 1 };
    const parsed = JSON.parse(raw) as Partial<StoredAudioPreferences>;
    return {
      enabled: parsed.enabled === true,
      volume: typeof parsed.volume === 'number' ? Math.min(1, Math.max(0, parsed.volume)) : 1,
    };
  } catch {
    return { enabled: false, volume: 1 };
  }
}

const audioFor = (name: GameSoundName, loop = false): HTMLAudioElement => {
  const audio = new Audio(gameSoundManifest[name]);
  audio.loop = loop;
  audio.preload = loop ? 'auto' : 'metadata';
  return audio;
};

export const GameAudioProvider = ({ children }: { children: ReactNode }) => {
  const initial = useMemo(readPreferences, []);
  // Browsers require a fresh user gesture after each page load. Keep volume
  // preference, but never force playback merely because a prior visit enabled it.
  const [enabled, setEnabled] = useState(false);
  const [volume, setVolumeState] = useState(initial.volume);
  const [blockedMessage, setBlockedMessage] = useState<string | null>(null);
  const enabledRef = useRef(false);
  const volumeRef = useRef(initial.volume);
  const desiredBackgroundRef = useRef<BackgroundTrack>(null);
  const activeBackgroundRef = useRef<BackgroundTrack>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const loopsRef = useRef<Record<Exclude<BackgroundTrack, null>, HTMLAudioElement>>({
    boardLoop: audioFor('boardLoop', true),
    answeringLoop: audioFor('answeringLoop', true),
  });
  const effectsRef = useRef<Set<HTMLAudioElement>>(new Set());
  const delayedEffectTimerRef = useRef<number | null>(null);

  const persist = useCallback((nextEnabled: boolean, nextVolume: number) => {
    window.localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ enabled: nextEnabled, volume: nextVolume } satisfies StoredAudioPreferences),
    );
  }, []);

  const applyLoopVolume = useCallback((duck = false) => {
    const gain = BACKGROUND_GAIN * volumeRef.current * (duck ? 0.25 : 1);
    Object.values(loopsRef.current).forEach((audio) => {
      audio.volume = gain;
    });
  }, []);

  const stopAll = useCallback(() => {
    if (delayedEffectTimerRef.current !== null) {
      window.clearTimeout(delayedEffectTimerRef.current);
      delayedEffectTimerRef.current = null;
    }
    Object.values(loopsRef.current).forEach((audio) => {
      audio.pause();
      audio.currentTime = 0;
    });
    effectsRef.current.forEach((audio) => {
      audio.pause();
      audio.currentTime = 0;
    });
    effectsRef.current.clear();
    activeBackgroundRef.current = null;
  }, []);

  const startBackground = useCallback(
    async (track: BackgroundTrack) => {
      desiredBackgroundRef.current = track;
      if (!enabledRef.current) return;
      if (track === activeBackgroundRef.current) return;
      Object.entries(loopsRef.current).forEach(([name, audio]) => {
        if (name !== track) {
          audio.pause();
          audio.currentTime = 0;
        }
      });
      activeBackgroundRef.current = null;
      if (!track) return;
      const audio = loopsRef.current[track];
      applyLoopVolume();
      try {
        await audio.play();
        activeBackgroundRef.current = track;
        setBlockedMessage(null);
      } catch {
        setBlockedMessage('Browser blocked sound. Select Enable sound and try again.');
      }
    },
    [applyLoopVolume],
  );

  const playEffect = useCallback(
    async (name: GameSoundName, after?: BackgroundTrack) => {
      if (!enabledRef.current) return;
      const audio = audioFor(name);
      audio.volume = EFFECT_GAIN * volumeRef.current;
      effectsRef.current.forEach((effect) => {
        effect.pause();
        effect.currentTime = 0;
      });
      effectsRef.current.clear();
      applyLoopVolume(true);
      effectsRef.current.add(audio);
      audio.addEventListener(
        'ended',
        () => {
          effectsRef.current.delete(audio);
          applyLoopVolume();
          if (after) void startBackground(after);
        },
        { once: true },
      );
      try {
        await audio.play();
      } catch {
        effectsRef.current.delete(audio);
        applyLoopVolume();
        setBlockedMessage('Browser blocked sound. Select Enable sound and try again.');
      }
    },
    [applyLoopVolume, startBackground],
  );

  const enableSound = useCallback(async () => {
    try {
      const AudioContextConstructor = window.AudioContext;
      if (!AudioContextConstructor) throw new Error('Web Audio API unavailable');
      audioContextRef.current ??= new AudioContextConstructor();
      await audioContextRef.current.resume();
      enabledRef.current = true;
      setEnabled(true);
      persist(true, volumeRef.current);
      setBlockedMessage(null);
      await startBackground(desiredBackgroundRef.current);
    } catch {
      enabledRef.current = false;
      setEnabled(false);
      persist(false, volumeRef.current);
      setBlockedMessage('Sound could not start. Try Enable sound again.');
    }
  }, [persist, startBackground]);

  const toggleMuted = useCallback(() => {
    const next = !enabledRef.current;
    enabledRef.current = next;
    setEnabled(next);
    persist(next, volumeRef.current);
    if (!next) {
      stopAll();
      return;
    }
    void enableSound();
  }, [enableSound, persist, stopAll]);

  const setVolume = useCallback(
    (next: number) => {
      const clamped = Math.min(1, Math.max(0, next));
      volumeRef.current = clamped;
      setVolumeState(clamped);
      persist(enabledRef.current, clamped);
      applyLoopVolume();
    },
    [applyLoopVolume, persist],
  );

  const syncGameState = useCallback(
    (state: GameLobbyState | null) => {
      if (!state || state.phase === 'finished' || state.phase === 'answer_reveal') {
        void startBackground(null);
        return;
      }
      if (
        state.phase === 'waiting_for_players' ||
        state.phase === 'host_selecting_starting_player' ||
        state.phase === 'player_selecting_prompt'
      ) {
        void startBackground('boardLoop');
        return;
      }
      void startBackground('answeringLoop');
    },
    [startBackground],
  );

  const playCue = useCallback(
    (cue: GameSoundCuePayload) => {
      switch (cue.cue) {
        case 'game_started':
          void playEffect('intro', 'boardLoop');
          break;
        case 'clue_selected':
          void playEffect('clueSelected', 'answeringLoop');
          break;
        case 'buzz_accepted':
          void playEffect('buzz', 'answeringLoop');
          break;
        case 'answer_correct':
          void startBackground(null);
          void playEffect('correct');
          break;
        case 'answer_wrong':
          void playEffect('wrong', 'answeringLoop');
          break;
        case 'answer_expired':
          // Expiry immediately leads to answer reveal. Do not restore the
          // answering loop after this cue finishes.
          void playEffect('timeExpired');
          break;
        case 'answer_revealed':
          void startBackground(null);
          if (effectsRef.current.size > 0) {
            if (delayedEffectTimerRef.current !== null) {
              window.clearTimeout(delayedEffectTimerRef.current);
            }
            delayedEffectTimerRef.current = window.setTimeout(() => {
              delayedEffectTimerRef.current = null;
              void playEffect('answerReveal');
            }, 450);
          } else {
            void playEffect('answerReveal');
          }
          break;
        case 'game_completed':
          void startBackground(null);
          void playEffect('gameComplete');
          break;
      }
    },
    [playEffect, startBackground],
  );

  useEffect(() => {
    return () => {
      stopAll();
      void audioContextRef.current?.close();
    };
  }, [stopAll]);

  const value = useMemo<GameAudioContextValue>(
    () => ({
      enabled,
      volume,
      blockedMessage,
      enableSound,
      toggleMuted,
      setVolume,
      syncGameState,
      playCue,
      stopAll,
    }),
    [
      blockedMessage,
      enableSound,
      enabled,
      playCue,
      setVolume,
      stopAll,
      syncGameState,
      toggleMuted,
      volume,
    ],
  );

  return <GameAudioContext.Provider value={value}>{children}</GameAudioContext.Provider>;
};
