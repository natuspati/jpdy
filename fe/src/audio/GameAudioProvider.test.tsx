import { act, fireEvent, render, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { buildGameState } from '@/test/fixtures/gameState';
import { useGameAudio } from './useGameAudio';
import { GameAudioProvider } from './GameAudioProvider';

class FakeAudio {
  static instances: FakeAudio[] = [];

  currentTime = 0;
  loop = false;
  preload = '';
  volume = 1;
  readonly pause = vi.fn();
  readonly play = vi.fn(async () => undefined);
  readonly addEventListener = vi.fn();

  constructor(readonly src: string) {
    FakeAudio.instances.push(this);
  }
}

class FakeAudioContext {
  resume = vi.fn(async () => undefined);
  close = vi.fn(async () => undefined);
}

const AudioHarness = () => {
  const { beginPromptMediaPlayback, enableSound, endPromptMediaPlayback, syncGameState } =
    useGameAudio();
  return (
    <>
      <button type="button" onClick={() => void enableSound()}>
        Enable
      </button>
      <button type="button" onClick={() => syncGameState(buildGameState())}>
        Board
      </button>
      <button type="button" onClick={() => beginPromptMediaPlayback('101:question')}>
        Begin first
      </button>
      <button type="button" onClick={() => beginPromptMediaPlayback('101:answer')}>
        Begin second
      </button>
      <button type="button" onClick={() => endPromptMediaPlayback('101:question')}>
        End first
      </button>
      <button type="button" onClick={() => endPromptMediaPlayback('101:answer')}>
        End second
      </button>
    </>
  );
};

describe('GameAudioProvider prompt-media coordination', () => {
  const originalAudio = globalThis.Audio;
  const originalAudioContext = window.AudioContext;

  beforeEach(() => {
    FakeAudio.instances = [];
    Object.defineProperty(globalThis, 'Audio', { configurable: true, value: FakeAudio });
    Object.defineProperty(window, 'AudioContext', {
      configurable: true,
      value: FakeAudioContext,
    });
  });

  afterEach(() => {
    Object.defineProperty(globalThis, 'Audio', { configurable: true, value: originalAudio });
    Object.defineProperty(window, 'AudioContext', {
      configurable: true,
      value: originalAudioContext,
    });
  });

  it('pauses the desired background loop until every active prompt medium releases it', async () => {
    const { getByRole } = render(
      <GameAudioProvider>
        <AudioHarness />
      </GameAudioProvider>,
    );

    fireEvent.click(getByRole('button', { name: 'Enable' }));
    fireEvent.click(getByRole('button', { name: 'Board' }));

    const boardLoop = FakeAudio.instances.find((audio) => audio.src.includes('board-loop'));
    expect(boardLoop).toBeDefined();
    if (!boardLoop) throw new Error('Board loop was not initialized');

    await waitFor(() => expect(boardLoop.play).toHaveBeenCalledOnce());

    fireEvent.click(getByRole('button', { name: 'Begin first' }));
    fireEvent.click(getByRole('button', { name: 'Begin second' }));
    expect(boardLoop.pause).toHaveBeenCalled();

    fireEvent.click(getByRole('button', { name: 'End first' }));
    await act(async () => undefined);
    expect(boardLoop.play).toHaveBeenCalledOnce();

    fireEvent.click(getByRole('button', { name: 'End second' }));
    await waitFor(() => expect(boardLoop.play).toHaveBeenCalledTimes(2));
  });
});
