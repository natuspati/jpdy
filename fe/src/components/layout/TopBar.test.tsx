import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import { GameAudioContext, type GameAudioContextValue } from '@/audio/gameAudioContext';
import { useAuthStore } from '@/store/authStore';
import TopBar from './TopBar';

vi.mock('@/hooks/useMe', () => ({
  useMe: () => ({ data: { username: 'alex' } }),
}));

vi.mock('@tanstack/react-query', () => ({
  useQueryClient: () => ({ clear: vi.fn() }),
}));

function audioValue(overrides: Partial<GameAudioContextValue> = {}): GameAudioContextValue {
  return {
    enabled: false,
    volume: 0.4,
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

const renderTopBar = (audio = audioValue()) =>
  render(
    <MemoryRouter>
      <GameAudioContext.Provider value={audio}>
        <TopBar />
      </GameAudioContext.Provider>
    </MemoryRouter>,
  );

describe('TopBar game sound controls', () => {
  it('enables sound when inactive and mutes when active', () => {
    useAuthStore.setState({
      token: 'token',
      userId: 1,
      expiresAt: Date.now() + 60_000,
    });
    const inactive = audioValue();
    const { rerender } = renderTopBar(inactive);

    fireEvent.click(screen.getByRole('button', { name: 'Enable game sound' }));
    expect(inactive.enableSound).toHaveBeenCalledOnce();

    const active = audioValue({ enabled: true });
    rerender(
      <MemoryRouter>
        <GameAudioContext.Provider value={active}>
          <TopBar />
        </GameAudioContext.Provider>
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByRole('button', { name: 'Mute game sound' }));
    expect(active.toggleMuted).toHaveBeenCalledOnce();
  });

  it('shows its vertical volume control on hover or focus, keeps it open while moving to it, and converts 0–100 values', () => {
    useAuthStore.setState({
      token: 'token',
      userId: 1,
      expiresAt: Date.now() + 60_000,
    });
    const audio = audioValue({ enabled: true, volume: 0.42 });
    renderTopBar(audio);

    const soundButton = screen.getByRole('button', { name: 'Mute game sound' });
    const menu = document.getElementById('game-sound-menu');
    if (!menu) throw new Error('Sound settings menu was not rendered');
    expect(menu).toHaveAttribute('aria-hidden', 'true');
    expect(menu).toHaveClass('left-1/2', '-translate-x-1/2', 'top-full', 'pt-2');

    fireEvent.mouseEnter(soundButton);
    expect(menu).toHaveAttribute('aria-hidden', 'false');
    const slider = screen.getByRole('slider', { name: 'Game volume' });
    expect(slider).toHaveValue('42');
    expect(slider).toHaveClass('sound-volume-slider');

    fireEvent.change(slider, { target: { value: '75' } });
    expect(audio.setVolume).toHaveBeenCalledWith(0.75);

    fireEvent.mouseLeave(soundButton, { relatedTarget: menu });
    fireEvent.mouseEnter(menu, { relatedTarget: soundButton });
    expect(menu).toHaveAttribute('aria-hidden', 'false');

    fireEvent.mouseLeave(soundButton.parentElement ?? soundButton);
    expect(menu).toHaveAttribute('aria-hidden', 'true');
    fireEvent.focus(soundButton);
    expect(menu).toHaveAttribute('aria-hidden', 'false');
  });
});
