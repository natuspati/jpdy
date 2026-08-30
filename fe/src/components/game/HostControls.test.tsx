import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { buildGameState } from '@/test/fixtures/gameState';
import HostControls from './HostControls';

describe('HostControls', () => {
  const controls = (state = buildGameState()) => ({
    state,
    currentUserId: state.host.user_id,
    onStart: vi.fn(),
    onSelectStarter: vi.fn(),
    onAdvanceAnswerReveal: vi.fn(),
    onJudge: vi.fn(),
  });

  it('shows only Start game while the lobby is waiting for players', () => {
    const props = controls();
    render(<HostControls {...props} />);

    expect(screen.getByRole('button', { name: 'Start game' })).toBeEnabled();
    expect(screen.queryByRole('button', { name: 'Accept' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Decline' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Next' })).not.toBeInTheDocument();
  });

  it('calls Accept and Decline only while a player is answering', async () => {
    const props = controls(
      buildGameState({
        phase: 'player_answering',
        answeringPlayerId: 2,
      }),
    );
    render(<HostControls {...props} />);

    await userEvent.click(screen.getByRole('button', { name: 'Accept' }));
    await userEvent.click(screen.getByRole('button', { name: 'Decline' }));
    expect(props.onJudge).toHaveBeenNthCalledWith(1, true);
    expect(props.onJudge).toHaveBeenNthCalledWith(2, false);
    expect(screen.getByRole('button', { name: 'Next' })).toBeDisabled();
  });

  it('uses generic next-player copy and excludes banned or disconnected choices', () => {
    const props = controls(
      buildGameState({
        phase: 'host_selecting_starting_player',
        players: [
          { user_id: 2, username: 'connected' },
          { user_id: 3, username: 'banned', is_banned: true },
          { user_id: 4, username: 'offline', connection_status: 'disconnected' },
        ],
      }),
    );
    render(<HostControls {...props} />);

    expect(screen.getByText('Choose starting player')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'connected' }));
    expect(props.onSelectStarter).toHaveBeenCalledWith(2);
    expect(screen.queryByRole('button', { name: 'banned' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'offline' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Accept' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Decline' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Next' })).not.toBeInTheDocument();
  });

  it('shows recovery waiting state when no eligible player remains', () => {
    const props = controls(
      buildGameState({
        phase: 'host_selecting_starting_player',
        players: [{ user_id: 2, username: 'offline', connection_status: 'disconnected' }],
      }),
    );
    render(<HostControls {...props} />);

    expect(
      screen.getByText(/waiting for a player to reconnect or be unbanned/i),
    ).toBeInTheDocument();
  });

  it('enables Next only during answer reveal', () => {
    const props = controls(
      buildGameState({
        phase: 'answer_reveal',
        currentPromptId: 101,
        resolvedPromptId: 101,
        resolvedAnswer: 'Category 1 A1',
        resolution: 'correct',
      }),
    );
    render(<HostControls {...props} />);

    fireEvent.click(screen.getByRole('button', { name: 'Next' }));
    expect(props.onAdvanceAnswerReveal).toHaveBeenCalledOnce();
    expect(screen.getByRole('button', { name: 'Accept' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Decline' })).toBeDisabled();
  });
});
