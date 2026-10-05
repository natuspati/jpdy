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
  it('toggles sound from the panel and shows the current state', () => {
    authenticate();
    const inactive = audioValue();
    const { rerender } = renderTopBar(inactive);

    fireEvent.click(screen.getByRole('button', { name: 'Game sound settings' }));
    fireEvent.click(screen.getByRole('button', { name: 'Sound off' }));
    expect(inactive.toggleMuted).toHaveBeenCalledOnce();

    rerender(
      <MemoryRouter>
        <GameAudioContext.Provider value={audioValue({ enabled: true })}>
          <TopBar />
        </GameAudioContext.Provider>
      </MemoryRouter>,
    );
    expect(screen.getByRole('button', { name: 'Sound on' })).toHaveAttribute(
      'aria-pressed',
      'true',
    );
  });

  it('opens the volume panel on tap, closes it on outside tap or Escape, and converts 0–100 values', () => {
    authenticate();
    const audio = audioValue({ enabled: true, volume: 0.42 });
    renderTopBar(audio);

    const openButton = screen.getByRole('button', { name: 'Game sound settings' });
    const menu = document.getElementById('game-sound-menu');
    if (!menu) throw new Error('Sound settings menu was not rendered');
    expect(menu).toHaveAttribute('aria-hidden', 'true');

    fireEvent.mouseEnter(openButton);
    expect(menu).toHaveAttribute('aria-hidden', 'true');

    fireEvent.click(openButton);
    expect(menu).toHaveAttribute('aria-hidden', 'false');
    const slider = screen.getByRole('slider', { name: 'Game volume' });
    expect(slider).toHaveValue('42');

    fireEvent.change(slider, { target: { value: '75' } });
    expect(audio.setVolume).toHaveBeenCalledWith(0.75);

    fireEvent.pointerDown(slider);
    expect(menu).toHaveAttribute('aria-hidden', 'false');

    fireEvent.pointerDown(document.body);
    expect(menu).toHaveAttribute('aria-hidden', 'true');

    fireEvent.click(openButton);
    expect(menu).toHaveAttribute('aria-hidden', 'false');
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(menu).toHaveAttribute('aria-hidden', 'true');
  });

  it('shows a blocked-sound message outside the panel', () => {
    authenticate();
    renderTopBar(audioValue({ blockedMessage: 'Sound could not start.' }));

    expect(screen.getByRole('status')).toHaveTextContent('Sound could not start.');
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
