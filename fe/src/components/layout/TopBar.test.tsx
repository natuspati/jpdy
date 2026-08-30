import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter, useLocation } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import { GameAudioContext, type GameAudioContextValue } from '@/audio/gameAudioContext';
import { useAuthStore } from '@/store/authStore';
import TopBar from './TopBar';

vi.mock('@/hooks/useMe', () => ({
  useMe: () => ({ data: { username: 'alex' } }),
}));

const { queryClient } = vi.hoisted(() => ({
  queryClient: { clear: vi.fn() },
}));

vi.mock('@tanstack/react-query', () => ({
  useQueryClient: () => queryClient,
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

const renderTopBar = (audio = audioValue(), initialEntry = '/') =>
  render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <GameAudioContext.Provider value={audio}>
        <TopBar />
      </GameAudioContext.Provider>
    </MemoryRouter>,
  );

function LocationDisplay() {
  const location = useLocation();
  return <output>{location.pathname}</output>;
}

const renderTopBarWithLocation = (initialEntry: string) =>
  render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <GameAudioContext.Provider value={audioValue()}>
        <TopBar />
        <LocationDisplay />
      </GameAudioContext.Provider>
    </MemoryRouter>,
  );

function authenticate() {
  useAuthStore.setState({
    token: 'token',
    userId: 1,
    expiresAt: Date.now() + 60_000,
  });
}

describe('TopBar', () => {
  it('enables sound when inactive and mutes when active', () => {
    authenticate();
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
    authenticate();
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

  it('orders lobby and category links after the brand and marks only the matching section active', () => {
    authenticate();
    const { unmount } = renderTopBar(audioValue(), '/');

    expect(screen.getByRole('banner').firstElementChild).toHaveClass('max-w-7xl');
    const links = screen.getAllByRole('link').map((link) => ({
      name: link.textContent,
      href: link.getAttribute('href'),
    }));
    expect(links).toEqual([
      { name: 'Jeopardy', href: '/' },
      { name: 'Lobbies', href: '/' },
      { name: 'Categories', href: '/categories' },
    ]);
    expect(screen.getByRole('link', { name: 'Lobbies' })).toHaveAttribute('aria-current', 'page');
    expect(screen.getByRole('link', { name: 'Categories' })).not.toHaveAttribute('aria-current');

    unmount();
    renderTopBar(audioValue(), '/categories/8');
    expect(screen.getByRole('link', { name: 'Lobbies' })).not.toHaveAttribute('aria-current');
    expect(screen.getByRole('link', { name: 'Categories' })).toHaveAttribute(
      'aria-current',
      'page',
    );
  });

  it('does not mark lobby or category navigation active in a game route', () => {
    authenticate();
    renderTopBar(audioValue(), '/lobby/12/details');

    expect(screen.getByRole('link', { name: 'Lobbies' })).not.toHaveAttribute('aria-current');
    expect(screen.getByRole('link', { name: 'Categories' })).not.toHaveAttribute('aria-current');
  });

  it('opens the account menu on hover and signs out through its keyboard-accessible menu item', () => {
    authenticate();
    queryClient.clear.mockClear();
    renderTopBarWithLocation('/categories');

    const accountButton = screen.getByRole('button', { name: 'alex' });
    const menu = document.getElementById('user-menu');
    if (!menu) throw new Error('Account menu was not rendered');
    expect(menu).toHaveAttribute('aria-hidden', 'true');

    fireEvent.mouseEnter(accountButton);
    expect(menu).toHaveAttribute('aria-hidden', 'false');
    const signOut = screen.getByRole('menuitem', { name: 'Sign out' });
    expect(signOut).toHaveAttribute('tabindex', '0');

    fireEvent.click(signOut);
    expect(queryClient.clear).toHaveBeenCalledOnce();
    expect(useAuthStore.getState().token).toBeNull();
    expect(screen.getByText('/')).toBeInTheDocument();
  });
});
