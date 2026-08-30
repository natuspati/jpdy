import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { buildGameState } from '@/test/fixtures/gameState';
import HostControls from './HostControls';

describe('HostControls', () => {
  it('uses generic next-player copy and excludes banned or disconnected choices', () => {
    const onSelectStarter = vi.fn();
    const state = buildGameState({
      phase: 'host_selecting_starting_player',
      players: [
        { user_id: 2, username: 'connected' },
        { user_id: 3, username: 'banned', is_banned: true },
        { user_id: 4, username: 'offline', connection_status: 'disconnected' },
      ],
    });
    render(
      <HostControls
        state={state}
        currentUserId={state.host.user_id}
        onStart={vi.fn()}
        onSelectStarter={onSelectStarter}
        onAdvanceAnswerReveal={vi.fn()}
      />,
    );

    expect(screen.getByText('Choose next player')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'connected' }));
    expect(onSelectStarter).toHaveBeenCalledWith(2);
    expect(screen.queryByRole('button', { name: 'banned' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'offline' })).not.toBeInTheDocument();
  });

  it('shows recovery waiting state when no eligible player remains', () => {
    const state = buildGameState({
      phase: 'host_selecting_starting_player',
      players: [{ user_id: 2, username: 'offline', connection_status: 'disconnected' }],
    });
    render(
      <HostControls
        state={state}
        currentUserId={state.host.user_id}
        onStart={vi.fn()}
        onSelectStarter={vi.fn()}
        onAdvanceAnswerReveal={vi.fn()}
      />,
    );

    expect(
      screen.getByText(/waiting for a player to reconnect or be unbanned/i),
    ).toBeInTheDocument();
  });

  it('shows Next prompt only for the host during answer reveal', () => {
    const onAdvanceAnswerReveal = vi.fn();
    const state = buildGameState({
      phase: 'answer_reveal',
      currentPromptId: 101,
      resolvedPromptId: 101,
      resolvedAnswer: 'Category 1 A1',
      resolution: 'correct',
    });
    render(
      <HostControls
        state={state}
        currentUserId={state.host.user_id}
        onStart={vi.fn()}
        onSelectStarter={vi.fn()}
        onAdvanceAnswerReveal={onAdvanceAnswerReveal}
      />,
    );

    fireEvent.click(screen.getByRole('button', { name: 'Next prompt' }));
    expect(onAdvanceAnswerReveal).toHaveBeenCalledOnce();
  });

  it('does not show Next prompt to a non-host during answer reveal', () => {
    const state = buildGameState({
      phase: 'answer_reveal',
      currentPromptId: 101,
      resolvedPromptId: 101,
      resolvedAnswer: 'Category 1 A1',
      resolution: 'correct',
    });
    render(
      <HostControls
        state={state}
        currentUserId={2}
        onStart={vi.fn()}
        onSelectStarter={vi.fn()}
        onAdvanceAnswerReveal={vi.fn()}
      />,
    );

    expect(screen.queryByRole('button', { name: 'Next prompt' })).not.toBeInTheDocument();
  });
});
