import { type ReactNode, useCallback, useEffect, useMemo, useRef, useState } from 'react';

import type { GameLobbyState, GameSoundCuePayload } from '@/schemas';
import { GameAudioContext, type GameAudioContextValue } from './gameAudioContext';
import { gameSoundManifest, type GameSoundName } from './gameSoundManifest';

const STORAGE_KEY = 'jpdy.game-audio-preferences';
const BACKGROUND_GAIN = 0.1;
const DUCKED_BACKGROUND_FACTOR = 0.25;
const EFFECT_GAIN = 0.2;
const UNLOCK_EVENTS = ['pointerup', 'touchend', 'click', 'keydown'] as const;
const BLOCKED_MESSAGE = 'Sound could not start. Tap the sound button to try again.';

type BackgroundTrack = 'boardLoop' | 'answeringLoop' | null;

interface StoredAudioPreferences {
  enabled: boolean;
  volume: number;
}

interface AudioGraph {
  ctx: AudioContext;
  music: GainNode;
  effects: GainNode;
  master: GainNode;
}

function readPreferences(): StoredAudioPreferences {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return { enabled: true, volume: 1 };
    const parsed = JSON.parse(raw) as Partial<StoredAudioPreferences>;
    return {
      enabled: parsed.enabled !== false,
      volume: typeof parsed.volume === 'number' ? Math.min(1, Math.max(0, parsed.volume)) : 1,
    };
  } catch {
    return { enabled: true, volume: 1 };
  }
}

const audioContextConstructor = (): typeof AudioContext | undefined =>
  window.AudioContext ??
  (window as Window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;

export const GameAudioProvider = ({ children }: { children: ReactNode }) => {
  const initial = useMemo(readPreferences, []);
  // Sound is on by default, but browsers only let audio start after a user gesture.
  // The first tap or key press anywhere resumes the context (see the unlock effect).
  const [enabled, setEnabled] = useState(initial.enabled);
  const [volume, setVolumeState] = useState(initial.volume);
  const [blockedMessage, setBlockedMessage] = useState<string | null>(null);
  const enabledRef = useRef(initial.enabled);
  const volumeRef = useRef(initial.volume);
  const desiredBackgroundRef = useRef<BackgroundTrack>(null);
  const activePromptMediaKeysRef = useRef<Set<string>>(new Set());
  const graphRef = useRef<AudioGraph | null>(null);
  const buffersRef = useRef<Map<GameSoundName, Promise<AudioBuffer>>>(new Map());
  const loopRef = useRef<{
    track: Exclude<BackgroundTrack, null>;
    source: AudioBufferSourceNode;
  }>();
  const effectRef = useRef<AudioBufferSourceNode | null>(null);
  const delayedEffectTimerRef = useRef<number | null>(null);

  const persist = useCallback((nextEnabled: boolean, nextVolume: number) => {
    try {
      window.localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({
          enabled: nextEnabled,
          volume: nextVolume,
        } satisfies StoredAudioPreferences),
      );
    } catch {
      // Storage can be unavailable (private mode); preferences then last for this visit only.
    }
  }, []);

  const loadBuffer = useCallback((ctx: AudioContext, name: GameSoundName) => {
    let pending = buffersRef.current.get(name);
    if (!pending) {
      pending = fetch(gameSoundManifest[name])
        .then((response) => response.arrayBuffer())
        .then((data) => ctx.decodeAudioData(data));
      buffersRef.current.set(name, pending);
      // Allow a retry on the next play if the download or decode failed.
      pending.catch(() => buffersRef.current.delete(name));
    }
    return pending;
  }, []);

  // Must be first called from a user gesture for the context to be allowed to start on iOS.
  const ensureGraph = useCallback((): AudioGraph => {
    if (graphRef.current) return graphRef.current;
    const Constructor = audioContextConstructor();
    if (!Constructor) throw new Error('Web Audio API unavailable');
    const ctx = new Constructor();
    const master = ctx.createGain();
    master.gain.value = volumeRef.current;
    master.connect(ctx.destination);
    const music = ctx.createGain();
    music.gain.value = BACKGROUND_GAIN;
    music.connect(master);
    const effects = ctx.createGain();
    effects.gain.value = EFFECT_GAIN;
    effects.connect(master);
    graphRef.current = { ctx, master, music, effects };
    (Object.keys(gameSoundManifest) as GameSoundName[]).forEach((name) => {
      loadBuffer(ctx, name).catch(() => undefined);
    });
    return graphRef.current;
  }, [loadBuffer]);

  const applyDuck = useCallback((duck: boolean) => {
    const graph = graphRef.current;
    if (graph) {
      graph.music.gain.value = BACKGROUND_GAIN * (duck ? DUCKED_BACKGROUND_FACTOR : 1);
    }
  }, []);

  const stopBackground = useCallback(() => {
    const loop = loopRef.current;
    loopRef.current = undefined;
    loop?.source.stop();
    loop?.source.disconnect();
  }, []);

  const stopEffect = useCallback(() => {
    const effect = effectRef.current;
    effectRef.current = null;
    effect?.stop();
    effect?.disconnect();
  }, []);

  const stopAll = useCallback(() => {
    if (delayedEffectTimerRef.current !== null) {
      window.clearTimeout(delayedEffectTimerRef.current);
      delayedEffectTimerRef.current = null;
    }
    stopBackground();
    stopEffect();
    applyDuck(false);
  }, [applyDuck, stopBackground, stopEffect]);

  const startBackground = useCallback(
    async (track: BackgroundTrack) => {
      desiredBackgroundRef.current = track;
      if (activePromptMediaKeysRef.current.size > 0) {
        stopBackground();
        return;
      }
      if (!enabledRef.current) return;
      if (track === (loopRef.current?.track ?? null)) return;
      stopBackground();
      if (!track) return;
      try {
        const { ctx, music } = ensureGraph();
        // Still locked: the unlock effect restarts the desired track on the first gesture.
        if (ctx.state !== 'running') return;
        const buffer = await loadBuffer(ctx, track);
        if (
          activePromptMediaKeysRef.current.size > 0 ||
          !enabledRef.current ||
          desiredBackgroundRef.current !== track ||
          loopRef.current
        ) {
          return;
        }
        const source = ctx.createBufferSource();
        source.buffer = buffer;
        source.loop = true;
        source.connect(music);
        source.start();
        loopRef.current = { track, source };
        setBlockedMessage(null);
      } catch {
        setBlockedMessage(BLOCKED_MESSAGE);
      }
    },
    [ensureGraph, loadBuffer, stopBackground],
  );

  const beginPromptMediaPlayback = useCallback(
    (playbackId: string) => {
      const alreadyPlayingPromptMedia = activePromptMediaKeysRef.current.size > 0;
      activePromptMediaKeysRef.current.add(playbackId);
      if (!alreadyPlayingPromptMedia) {
        stopBackground();
      }
    },
    [stopBackground],
  );

  const endPromptMediaPlayback = useCallback(
    (playbackId: string) => {
      if (!activePromptMediaKeysRef.current.delete(playbackId)) return;
      if (activePromptMediaKeysRef.current.size > 0) return;

      // Let a replacing media element report its `play` event before a
      // background loop is restored. This avoids an audible restart between
      // rapid media replacements while still restoring music after a real end,
      // pause, error, or unmount.
      void Promise.resolve().then(() => {
        if (activePromptMediaKeysRef.current.size === 0) {
          void startBackground(desiredBackgroundRef.current);
        }
      });
    },
    [startBackground],
  );

  const playEffect = useCallback(
    async (name: GameSoundName, after?: BackgroundTrack) => {
      if (!enabledRef.current) return;
      try {
        const { ctx, effects } = ensureGraph();
        if (ctx.state !== 'running') return;
        const buffer = await loadBuffer(ctx, name);
        if (!enabledRef.current) return;
        stopEffect();
        const source = ctx.createBufferSource();
        source.buffer = buffer;
        source.connect(effects);
        source.onended = () => {
          if (effectRef.current !== source) return;
          effectRef.current = null;
          applyDuck(false);
          if (after) void startBackground(after);
        };
        effectRef.current = source;
        applyDuck(true);
        source.start();
      } catch {
        applyDuck(false);
        setBlockedMessage(BLOCKED_MESSAGE);
      }
    },
    [applyDuck, ensureGraph, loadBuffer, startBackground, stopEffect],
  );

  // Starts the context inside a user gesture. iOS also wants a buffer played in the same
  // gesture, so a silent one-sample buffer goes out right after `resume()` is called.
  const unlock = useCallback(async () => {
    const { ctx } = ensureGraph();
    const resumed = ctx.resume();
    const silent = ctx.createBufferSource();
    silent.buffer = ctx.createBuffer(1, 1, 22050);
    silent.connect(ctx.destination);
    silent.start(0);
    await resumed;
  }, [ensureGraph]);

  const enableSound = useCallback(async () => {
    enabledRef.current = true;
    setEnabled(true);
    persist(true, volumeRef.current);
    try {
      await unlock();
      setBlockedMessage(null);
      await startBackground(desiredBackgroundRef.current);
    } catch {
      setBlockedMessage(BLOCKED_MESSAGE);
    }
  }, [persist, startBackground, unlock]);

  const toggleMuted = useCallback(() => {
    if (!enabledRef.current) {
      void enableSound();
      return;
    }
    enabledRef.current = false;
    setEnabled(false);
    persist(false, volumeRef.current);
    stopAll();
  }, [enableSound, persist, stopAll]);

  const setVolume = useCallback(
    (next: number) => {
      const clamped = Math.min(1, Math.max(0, next));
      volumeRef.current = clamped;
      setVolumeState(clamped);
      persist(enabledRef.current, clamped);
      if (graphRef.current) graphRef.current.master.gain.value = clamped;
    },
    [persist],
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
          if (effectRef.current) {
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

  // Autoplay policy: with sound on by default, the first gesture anywhere unlocks audio.
  useEffect(() => {
    const onGesture = () => {
      if (!enabledRef.current || graphRef.current?.ctx.state === 'running') return;
      unlock()
        .then(() => startBackground(desiredBackgroundRef.current))
        .catch(() => setBlockedMessage(BLOCKED_MESSAGE));
    };
    UNLOCK_EVENTS.forEach((type) => window.addEventListener(type, onGesture));
    return () => UNLOCK_EVENTS.forEach((type) => window.removeEventListener(type, onGesture));
  }, [startBackground, unlock]);

  useEffect(() => {
    const activePromptMediaKeys = activePromptMediaKeysRef.current;
    const buffers = buffersRef.current;
    return () => {
      stopAll();
      activePromptMediaKeys.clear();
      buffers.clear();
      void graphRef.current?.ctx.close();
      graphRef.current = null;
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
      beginPromptMediaPlayback,
      endPromptMediaPlayback,
      stopAll,
    }),
    [
      beginPromptMediaPlayback,
      blockedMessage,
      endPromptMediaPlayback,
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
