import { act, fireEvent, render, waitFor } from '@testing-library/react';
import { useEffect } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { buildGameState } from '@/test/fixtures/gameState';
import { useGameAudio } from './useGameAudio';
import { GameAudioProvider } from './GameAudioProvider';

interface FakeBuffer {
  url: string;
}

class FakeBufferSource {
  static instances: FakeBufferSource[] = [];

  buffer: FakeBuffer | null = null;
  loop = false;
  onended: (() => void) | null = null;
  readonly connect = vi.fn();
  readonly disconnect = vi.fn();
  readonly start = vi.fn();
  readonly stop = vi.fn();

  constructor() {
    FakeBufferSource.instances.push(this);
  }
}

const loops = () =>
  FakeBufferSource.instances.filter((source) => source.loop && source.buffer !== null);

class FakeAudioContext {
  static instances: FakeAudioContext[] = [];

  state: 'suspended' | 'running' = 'suspended';
  readonly destination = {};
  readonly masterGains: { gain: { value: number } }[] = [];
  readonly resume = vi.fn(async () => {
    this.state = 'running';
  });
  readonly close = vi.fn(async () => undefined);
  readonly decodeAudioData = vi.fn(async (data: FakeBuffer) => data);

  constructor() {
    FakeAudioContext.instances.push(this);
  }

  createGain() {
    const node = { gain: { value: 1 }, connect: vi.fn(), disconnect: vi.fn() };
    this.masterGains.push(node);
    return node;
  }

  createBuffer() {
    return { url: 'silent' };
  }

  createBufferSource() {
    return new FakeBufferSource();
  }
}

const AudioHarness = () => {
  const {
    beginPromptMediaPlayback,
    enableSound,
    endPromptMediaPlayback,
    setVolume,
    syncGameState,
    toggleMuted,
  } = useGameAudio();
  return (
    <>
      <button type="button" onClick={() => void enableSound()}>
        Enable
      </button>
      <button type="button" onClick={toggleMuted}>
        Toggle
      </button>
      <button type="button" onClick={() => setVolume(0.5)}>
        Half volume
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

const renderAudio = () =>
  render(
    <GameAudioProvider>
      <AudioHarness />
    </GameAudioProvider>,
  );

describe('GameAudioProvider', () => {
  const originalAudioContext = window.AudioContext;

  beforeEach(() => {
    FakeBufferSource.instances = [];
    FakeAudioContext.instances = [];
    window.localStorage.clear();
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string) => ({ arrayBuffer: async () => ({ url }) })),
    );
    Object.defineProperty(window, 'AudioContext', {
      configurable: true,
      value: FakeAudioContext,
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    Object.defineProperty(window, 'AudioContext', {
      configurable: true,
      value: originalAudioContext,
    });
  });

  it('pauses the desired background loop until every active prompt medium releases it', async () => {
    const { getByRole } = renderAudio();

    fireEvent.click(getByRole('button', { name: 'Enable' }));
    fireEvent.click(getByRole('button', { name: 'Board' }));

    await waitFor(() => expect(loops()).toHaveLength(1));
    const boardLoop = loops()[0];
    expect((boardLoop.buffer as FakeBuffer).url).toContain('board-loop');
    expect(boardLoop.start).toHaveBeenCalledOnce();

    fireEvent.click(getByRole('button', { name: 'Begin first' }));
    fireEvent.click(getByRole('button', { name: 'Begin second' }));
    expect(boardLoop.stop).toHaveBeenCalled();

    fireEvent.click(getByRole('button', { name: 'End first' }));
    await act(async () => undefined);
    expect(loops()).toHaveLength(1);

    fireEvent.click(getByRole('button', { name: 'End second' }));
    await waitFor(() => expect(loops()).toHaveLength(2));
  });

  it('is on by default and starts the desired loop on the first user gesture', async () => {
    // Sync from an effect (no gesture), as LobbyPage does when the state first arrives.
    const SyncOnMount = () => {
      const { syncGameState } = useGameAudio();
      useEffect(() => {
        syncGameState(buildGameState());
      }, [syncGameState]);
      return null;
    };
    render(
      <GameAudioProvider>
        <SyncOnMount />
      </GameAudioProvider>,
    );
    await act(async () => undefined);
    expect(loops()).toHaveLength(0);

    act(() => {
      window.dispatchEvent(new Event('pointerup'));
    });

    await waitFor(() => expect(loops()).toHaveLength(1));
    expect(FakeAudioContext.instances[0].resume).toHaveBeenCalled();
    expect((loops()[0].buffer as FakeBuffer).url).toContain('board-loop');
  });

  it('does not start sound when the stored preference is off, and the toggle turns it on', async () => {
    window.localStorage.setItem(
      'jpdy.game-audio-preferences',
      JSON.stringify({ enabled: false, volume: 1 }),
    );
    const { getByRole } = renderAudio();

    fireEvent.click(getByRole('button', { name: 'Board' }));
    act(() => {
      window.dispatchEvent(new Event('pointerup'));
    });
    await act(async () => undefined);
    expect(loops()).toHaveLength(0);

    fireEvent.click(getByRole('button', { name: 'Toggle' }));
    await waitFor(() => expect(loops()).toHaveLength(1));
  });

  it('applies the volume to the master gain node, which also works on iOS', async () => {
    const { getByRole } = renderAudio();

    fireEvent.click(getByRole('button', { name: 'Enable' }));
    await waitFor(() => expect(FakeAudioContext.instances).toHaveLength(1));
    fireEvent.click(getByRole('button', { name: 'Half volume' }));

    expect(FakeAudioContext.instances[0].masterGains[0].gain.value).toBe(0.5);
    expect(JSON.parse(window.localStorage.getItem('jpdy.game-audio-preferences') ?? '{}')).toEqual({
      enabled: true,
      volume: 0.5,
    });
  });
});
