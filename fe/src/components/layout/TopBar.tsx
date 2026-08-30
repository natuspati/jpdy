import { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Link, useLocation, useNavigate } from 'react-router-dom';

import { useGameAudio } from '@/audio/useGameAudio';
import { useAuth } from '@/hooks/useAuth';
import { useMe } from '@/hooks/useMe';

const SoundOnIcon = () => (
  <svg aria-hidden="true" viewBox="0 0 24 24" className="h-5 w-5 fill-current">
    <path d="M4 9v6h4l5 4V5L8 9H4Zm12.5 3c0-1.77-1-3.29-2.5-4.03v8.05A4.48 4.48 0 0 0 16.5 12ZM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.5 7-8.77s-2.99-7.86-7-8.77Z" />
  </svg>
);

const SoundOffIcon = () => (
  <svg aria-hidden="true" viewBox="0 0 24 24" className="h-5 w-5 fill-current">
    <path d="M16.5 12c0-1.77-1-3.29-2.5-4.03v2.45l2.45 2.45c.03-.28.05-.57.05-.87ZM19 12c0 .94-.2 1.82-.55 2.63l1.51 1.51A8.89 8.89 0 0 0 21 12c0-4.27-2.99-7.86-7-8.77v2.06A6.95 6.95 0 0 1 19 12ZM3.27 2 2 3.27 7.73 9H4v6h4l5 4v-5.73L17.73 18 19 16.73 3.27 2ZM13 5l-2.09 1.67L13 8.76V5Z" />
  </svg>
);

const TopBar = () => {
  const { isAuthed, signOut } = useAuth();
  const { data: me } = useMe();
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const { blockedMessage, enableSound, enabled, setVolume, toggleMuted, volume } = useGameAudio();
  const [soundMenuOpen, setSoundMenuOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);

  const handleSignOut = () => {
    signOut();
    queryClient.clear();
    navigate('/');
  };

  const handleSoundBlur = (event: React.FocusEvent<HTMLDivElement>) => {
    if (!event.currentTarget.contains(event.relatedTarget)) {
      setSoundMenuOpen(false);
    }
  };

  const handleUserBlur = (event: React.FocusEvent<HTMLDivElement>) => {
    if (!event.currentTarget.contains(event.relatedTarget)) {
      setUserMenuOpen(false);
    }
  };

  const volumePercent = Math.round(volume * 100);
  const soundIsAudible = enabled && volume > 0;
  const isLobbiesActive = location.pathname === '/';
  const isCategoriesActive =
    location.pathname === '/categories' || location.pathname.startsWith('/categories/');
  const navLinkClass = (isActive: boolean): string =>
    [
      'rounded-md px-2 py-1 text-sm font-medium transition-colors',
      isActive
        ? 'bg-slate-800 text-amber-300'
        : 'text-slate-300 hover:bg-slate-800 hover:text-amber-300',
    ].join(' ');

  return (
    <header className="sticky top-0 z-40 border-b border-slate-800 bg-slate-950/90 backdrop-blur">
      <div className="mx-auto flex w-full max-w-7xl items-center justify-between px-4 py-3 sm:px-6">
        <div className="flex min-w-0 items-center gap-1 sm:gap-2">
          <Link to="/" className="shrink-0 text-lg font-bold text-amber-400">
            Jeopardy
          </Link>
          {isAuthed ? (
            <nav aria-label="Primary navigation" className="flex items-center gap-1">
              <Link
                to="/"
                aria-current={isLobbiesActive ? 'page' : undefined}
                className={navLinkClass(isLobbiesActive)}
              >
                Lobbies
              </Link>
              <Link
                to="/categories"
                aria-current={isCategoriesActive ? 'page' : undefined}
                className={navLinkClass(isCategoriesActive)}
              >
                Categories
              </Link>
            </nav>
          ) : null}
        </div>
        {isAuthed ? (
          <div className="flex items-center gap-2 sm:gap-3">
            <div
              className="relative"
              onMouseEnter={() => setSoundMenuOpen(true)}
              onMouseLeave={() => setSoundMenuOpen(false)}
              onFocusCapture={() => setSoundMenuOpen(true)}
              onBlur={handleSoundBlur}
            >
              <button
                type="button"
                aria-label={enabled ? 'Mute game sound' : 'Enable game sound'}
                aria-controls="game-sound-menu"
                aria-expanded={soundMenuOpen}
                onClick={() => {
                  if (enabled) {
                    toggleMuted();
                    return;
                  }
                  void enableSound();
                }}
                className="inline-flex h-9 w-9 items-center justify-center rounded-md text-slate-300 transition-colors hover:bg-slate-800 hover:text-amber-300 focus:outline-none focus:ring-2 focus:ring-amber-400"
              >
                {soundIsAudible ? <SoundOnIcon /> : <SoundOffIcon />}
              </button>
              <div
                id="game-sound-menu"
                role="region"
                aria-label="Game sound settings"
                aria-hidden={!soundMenuOpen}
                className={`absolute left-1/2 top-full z-50 w-14 -translate-x-1/2 pt-2 ${
                  soundMenuOpen ? '' : 'pointer-events-none invisible'
                }`}
              >
                <div className="flex w-14 flex-col items-center gap-2 rounded-lg border border-slate-700 bg-slate-900 p-3 shadow-xl">
                  <label className="sr-only" htmlFor="game-volume">
                    Game volume
                  </label>
                  <input
                    id="game-volume"
                    aria-label="Game volume"
                    tabIndex={soundMenuOpen ? 0 : -1}
                    className="sound-volume-slider accent-amber-400"
                    type="range"
                    min="0"
                    max="100"
                    value={volumePercent}
                    onChange={(event) => setVolume(Number(event.target.value) / 100)}
                  />
                  <span className="text-xs font-semibold tabular-nums text-slate-300">
                    {volumePercent}
                  </span>
                  {blockedMessage ? (
                    <p className="w-40 text-center text-xs text-rose-300">{blockedMessage}</p>
                  ) : null}
                </div>
              </div>
            </div>
            <div
              className="relative"
              onMouseEnter={() => setUserMenuOpen(true)}
              onMouseLeave={() => setUserMenuOpen(false)}
              onFocusCapture={() => setUserMenuOpen(true)}
              onBlur={handleUserBlur}
            >
              <button
                type="button"
                aria-controls="user-menu"
                aria-expanded={userMenuOpen}
                aria-haspopup="menu"
                className="inline-flex max-w-32 items-center truncate rounded-md px-2 py-1 text-sm font-medium text-slate-300 transition-colors hover:bg-slate-800 hover:text-amber-300 focus:outline-none focus:ring-2 focus:ring-amber-400"
              >
                {me?.username ?? 'Account'}
              </button>
              <div
                id="user-menu"
                role="menu"
                aria-label="Account menu"
                aria-hidden={!userMenuOpen}
                className={`absolute right-0 top-full z-50 min-w-28 pt-2 ${
                  userMenuOpen ? '' : 'pointer-events-none invisible'
                }`}
              >
                <div className="rounded-lg border border-slate-700 bg-slate-900 p-1 shadow-xl">
                  <button
                    type="button"
                    role="menuitem"
                    tabIndex={userMenuOpen ? 0 : -1}
                    className="w-full rounded-md px-3 py-2 text-left text-sm font-medium text-slate-200 transition-colors hover:bg-slate-800 hover:text-amber-300 focus:outline-none focus:ring-2 focus:ring-amber-400"
                    onClick={handleSignOut}
                  >
                    Sign out
                  </button>
                </div>
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </header>
  );
};

export default TopBar;
