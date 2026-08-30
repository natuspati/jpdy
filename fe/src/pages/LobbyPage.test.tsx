import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import { GameAudioContext, type GameAudioContextValue } from '@/audio/gameAudioContext';
import { buildGameState } from '@/test/fixtures/gameState';
import LobbyPage from './LobbyPage';

const socketState = vi.hoisted(() => ({
  state: null as unknown,
  hostAnswerKey: null as { expected_answer: string } | null,
  soundCue: null,
  lobbyDeleted: false,
  status: 'open' as const,
  reason: null as string | null,
  emit: vi.fn(() => true),
  reconnect: vi.fn(),
}));

vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({ token: 'token', userId: 2 }),
}));

vi.mock('@/hooks/useLobbySocket', () => ({
  useLobbySocket: () => socketState,
}));

vi.mock('@/store/toastStore', () => ({
  toastSuccess: vi.fn(),
}));

function audioValue(): GameAudioContextValue {
  return {
    enabled: false,
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
  };
}

const renderLobby = () =>
  render(
    <MemoryRouter initialEntries={['/lobby/100']}>
      <GameAudioContext.Provider value={audioValue()}>
        <Routes>
          <Route path="/lobby/:id" element={<LobbyPage />} />
        </Routes>
      </GameAudioContext.Provider>
    </MemoryRouter>,
  );

describe('LobbyPage active-game layout', () => {
  it('places player tiles above a board, status-only side panel, and a buzzer below both', () => {
    socketState.state = buildGameState({
      phase: 'player_selecting_prompt',
      selectingPlayerId: 2,
    });
    socketState.status = 'open';
    renderLobby();

    const layout = screen.getByTestId('active-game-layout');
    const players = screen.getByRole('region', { name: 'Players' });
    expect(layout.firstElementChild).toBe(players);
    expect(screen.getByRole('button', { name: /buzz/i })).toBeDisabled();
    expect(screen.getByText('Wait for a clue to be selected.')).toBeInTheDocument();

    const sidePanel = screen.getByTestId('side-panel');
    const sections = Array.from(sidePanel.children).map((child) =>
      child.getAttribute('data-panel-section'),
    );
    expect(sections).toEqual(['countdown', 'game-status', 'chat-placeholder']);
    expect(screen.getByText('Chat')).toBeInTheDocument();
    expect(screen.getByText('Coming soon.')).toBeInTheDocument();
    expect(screen.getByTestId('game-actions').previousElementSibling).toBe(sidePanel.parentElement);
  });

  it('keeps the buzzer rendered and enables it only during buzz_open', () => {
    socketState.state = buildGameState({ phase: 'buzz_open' });
    socketState.status = 'open';
    renderLobby();

    expect(screen.getByRole('button', { name: /buzz/i })).toBeEnabled();
  });
});
