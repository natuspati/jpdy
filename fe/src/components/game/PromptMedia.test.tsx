import { fireEvent, render } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { GameAudioContext, type GameAudioContextValue } from '@/audio/gameAudioContext';
import PromptMedia from './PromptMedia';

function audioContextValue(overrides: Partial<GameAudioContextValue> = {}): GameAudioContextValue {
  return {
    enabled: true,
    volume: 1,
    blockedMessage: null,
    enableSound: vi.fn(async () => undefined),
    toggleMuted: vi.fn(),
    setVolume: vi.fn(),
    syncGameState: vi.fn(),
    playCue: vi.fn(),
    beginPromptMediaPlayback: vi.fn(),
    endPromptMediaPlayback: vi.fn(),
    stopAll: vi.fn(),
    ...overrides,
  };
}

describe('PromptMedia', () => {
  const media = {
    asset_id: 7,
    url: '/media/clue.mp3',
    mime_type: 'audio/mpeg',
    filename: 'clue.mp3',
  };

  it('autoplays game media once when sound is enabled without replacing it on parent rerender', () => {
    const value = audioContextValue();
    const { rerender } = render(
      <GameAudioContext.Provider value={value}>
        <PromptMedia contentType="audio" media={media} alt="Audio clue" playbackId="101:question" />
      </GameAudioContext.Provider>,
    );

    const audio = document.querySelector('audio');
    expect(audio).not.toBeNull();
    if (!audio) throw new Error('Audio element was not rendered');
    expect(audio).toHaveProperty('autoplay', true);

    rerender(
      <GameAudioContext.Provider value={value}>
        <PromptMedia contentType="audio" media={media} alt="Audio clue" playbackId="101:question" />
      </GameAudioContext.Provider>,
    );

    expect(document.querySelector('audio')).toBe(audio);
  });

  it('coordinates play, pause, error, and unmount with game background audio', () => {
    const beginPromptMediaPlayback = vi.fn();
    const endPromptMediaPlayback = vi.fn();
    const value = audioContextValue({ beginPromptMediaPlayback, endPromptMediaPlayback });
    const { unmount } = render(
      <GameAudioContext.Provider value={value}>
        <PromptMedia contentType="audio" media={media} alt="Audio clue" playbackId="101:question" />
      </GameAudioContext.Provider>,
    );

    const audio = document.querySelector('audio');
    expect(audio).not.toBeNull();
    if (!audio) throw new Error('Audio element was not rendered');
    fireEvent.play(audio);
    fireEvent.pause(audio);
    fireEvent.ended(audio);
    fireEvent.error(audio);
    unmount();

    expect(beginPromptMediaPlayback).toHaveBeenCalledWith('101:question');
    expect(endPromptMediaPlayback).toHaveBeenCalledWith('101:question');
    expect(endPromptMediaPlayback).toHaveBeenCalledTimes(4);
  });

  it('follows the global volume and sound toggle, including for a replacement element', () => {
    const renderMedia = (value: GameAudioContextValue, playbackId: string) => (
      <GameAudioContext.Provider value={value}>
        <PromptMedia contentType="video" media={media} alt="Video clue" playbackId={playbackId} />
      </GameAudioContext.Provider>
    );
    const { rerender } = render(renderMedia(audioContextValue({ volume: 0.4 }), '101:question'));
    const first = document.querySelector('video');
    if (!first) throw new Error('Video element was not rendered');
    expect(first.volume).toBe(0.4);
    expect(first.muted).toBe(false);

    rerender(renderMedia(audioContextValue({ volume: 0.4, enabled: false }), '101:question'));
    expect(first.muted).toBe(true);

    rerender(renderMedia(audioContextValue({ volume: 0 }), '101:question'));
    expect(first.muted).toBe(true);

    rerender(renderMedia(audioContextValue({ volume: 0.7 }), '101:answer'));
    const second = document.querySelector('video');
    expect(second).not.toBe(first);
    expect(second?.volume).toBe(0.7);
    expect(second?.muted).toBe(false);
  });

  it('leaves editor-style previews manually playable when no game playback identity is supplied', () => {
    const value = audioContextValue();
    render(
      <GameAudioContext.Provider value={value}>
        <PromptMedia contentType="audio" media={media} alt="Audio preview" />
      </GameAudioContext.Provider>,
    );

    expect(document.querySelector('audio')).toHaveProperty('autoplay', false);
  });
});
