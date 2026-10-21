import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { buildFinalGameState } from '@/test/fixtures/gameState';
import FinalRoundPanel from './FinalRoundPanel';

describe('FinalRoundPanel', () => {
  it('commits an integer wager from 0 to the top score and waits for server confirmation', () => {
    const state = buildFinalGameState();
    const emit = vi.fn(() => true);
    const { rerender } = render(<FinalRoundPanel state={state} userId={2} connected emit={emit} />);
    expect(screen.queryByText('The final question')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Pass' })).not.toBeInTheDocument();
    const wager = screen.getByLabelText('Your Final wager');
    expect(wager).toHaveValue(0);
    fireEvent.change(wager, { target: { value: '-1' } });
    expect(screen.getByRole('button', { name: 'Bet' })).toBeDisabled();
    fireEvent.change(wager, { target: { value: '1001' } });
    expect(screen.getByRole('button', { name: 'Bet' })).toBeDisabled();
    fireEvent.change(wager, { target: { value: '1000' } });
    fireEvent.click(screen.getByRole('button', { name: 'Bet' }));
    expect(emit).toHaveBeenLastCalledWith('submit_final_wager', { amount: 1000 });
    fireEvent.change(wager, { target: { value: '0' } });
    fireEvent.click(screen.getByRole('button', { name: 'Bet' }));
    expect(emit).toHaveBeenLastCalledWith('submit_final_wager', { amount: 0 });

    rerender(
      <FinalRoundPanel
        state={state}
        userId={2}
        connected
        emit={emit}
        pendingCommand="submit_final_wager"
      />,
    );
    expect(screen.getByRole('button', { name: 'Bet' })).toBeDisabled();

    state.final_round!.players[0].decision_submitted = true;
    state.final_round!.players[0].wager = 200;
    rerender(<FinalRoundPanel state={state} userId={2} connected emit={emit} />);
    expect(screen.getByRole('status')).toHaveTextContent('✓ 200');
    expect(screen.queryByRole('spinbutton')).not.toBeInTheDocument();
  });

  it('restores own accepted secrets without showing opponents values to players or host', () => {
    const state = buildFinalGameState('final_answering');
    state.final_round!.players[0].answer_submitted = true;
    state.final_round!.players[0].answer = 'Own accepted answer';
    // Defense in depth: even an unparsed object must not display opponent secrets.
    state.final_round!.players[1].wager = 987;
    state.final_round!.players[1].answer = 'Opponent secret';
    state.final_round!.players[1].answer_submitted = true;
    const emit = vi.fn(() => true);
    const { rerender } = render(<FinalRoundPanel state={state} userId={2} connected emit={emit} />);
    expect(screen.getByText('Your wager: 200')).toBeInTheDocument();
    expect(screen.getByText(/Own accepted answer/)).toBeInTheDocument();
    expect(screen.queryByText(/Opponent secret|987/)).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Submit' })).not.toBeInTheDocument();

    rerender(<FinalRoundPanel state={state} userId={1} connected emit={emit} />);
    expect(screen.queryByText(/Own accepted answer|Opponent secret|987/)).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Final progress')).not.toBeInTheDocument();
  });

  it('submits written text once, enforces its cap, and displays errors without losing a draft', () => {
    const state = buildFinalGameState('final_answering');
    const emit = vi.fn(() => true);
    const { rerender } = render(<FinalRoundPanel state={state} userId={2} connected emit={emit} />);
    const answer = screen.getByLabelText('Your Final answer');
    expect(answer).toHaveAttribute('maxlength', '256');
    fireEvent.change(answer, { target: { value: 'My answer' } });
    fireEvent.click(screen.getByRole('button', { name: 'Submit' }));
    expect(emit).toHaveBeenCalledWith('submit_final_answer', { answer: 'My answer' });
    rerender(
      <FinalRoundPanel
        state={state}
        userId={2}
        connected
        emit={emit}
        pendingCommand="submit_final_answer"
      />,
    );
    expect(answer).toBeDisabled();
    rerender(
      <FinalRoundPanel state={state} userId={2} connected emit={emit} commandError="Try again" />,
    );
    expect(screen.getByRole('alert')).toHaveTextContent('Try again');
    expect(answer).toHaveValue('My answer');
    expect(answer).toBeEnabled();
  });

  it('makes sit-out/ineligible/removed players read-only and closes expired submissions', () => {
    const state = buildFinalGameState('final_answering');
    const emit = vi.fn(() => true);
    const { rerender } = render(<FinalRoundPanel state={state} userId={3} connected emit={emit} />);
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
    state.final_round!.players[0].removed = true;
    rerender(<FinalRoundPanel state={state} userId={2} connected emit={emit} />);
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
    state.final_round!.players[0].removed = false;
    state.timer_deadline = new Date(Date.now() - 1000).toISOString();
    rerender(<FinalRoundPanel state={state} userId={2} connected emit={emit} />);
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
  });

  it('fences judgment and explicit Next/Finish by the current player and keeps empty outcomes visible', () => {
    const state = buildFinalGameState('final_reveal');
    const emit = vi.fn(() => true);
    const { rerender } = render(<FinalRoundPanel state={state} userId={1} connected emit={emit} />);
    expect(screen.getByLabelText('Correct Final answer')).toHaveTextContent('The correct answer');
    expect(screen.getByRole('button', { name: 'Next' })).toBeDisabled();
    expect(screen.getByLabelText('Current Final response')).toHaveTextContent(
      'alice (200): A written response',
    );
    fireEvent.click(screen.getByRole('button', { name: 'Accept' }));
    expect(emit).toHaveBeenCalledWith('judge_final_answer', { user_id: 2, correct: true });
    const player = state.final_round!.players[0];
    Object.assign(player, { correct: false, score_delta: -200, updated_score: 300, answer: '' });
    state.final_round!.is_last_reveal = true;
    rerender(<FinalRoundPanel state={state} userId={1} connected emit={emit} />);
    expect(screen.getByLabelText('Current Final response')).toHaveTextContent(
      'alice (200): Not submitted',
    );
    expect(screen.getByTestId('final-showdown')).toHaveClass('animate-verdict-wrong');
    expect(screen.getByRole('button', { name: 'Accept' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Decline' })).toBeDisabled();
    fireEvent.click(screen.getByRole('button', { name: 'Finish' }));
    expect(emit).toHaveBeenLastCalledWith('advance_final_reveal', { user_id: 2 });
  });

  it('renders Final question media during answering and canonical media only during reveal', () => {
    const state = buildFinalGameState('final_answering');
    const media = {
      asset_id: 1,
      url: '/question.png',
      mime_type: 'image/png',
      filename: 'question',
    };
    Object.assign(state.categories[1].prompts[0], {
      question_type: 'image',
      question_media: media,
    });
    Object.assign(state.final_round!, {
      correct_answer: 'Canonical image',
      correct_answer_type: 'image',
      correct_answer_media: { ...media, url: '/canonical.png' },
    });
    const emit = vi.fn(() => true);
    const { rerender } = render(<FinalRoundPanel state={state} userId={3} connected emit={emit} />);
    expect(screen.getByRole('img', { name: 'The final question' })).toHaveAttribute(
      'src',
      '/question.png',
    );
    expect(
      screen.queryByRole('img', { name: 'Correct answer: Canonical image' }),
    ).not.toBeInTheDocument();
    state.phase = 'final_reveal';
    rerender(<FinalRoundPanel state={state} userId={3} connected emit={emit} />);
    expect(screen.getByRole('img', { name: 'Correct answer: Canonical image' })).toHaveAttribute(
      'src',
      '/canonical.png',
    );
  });
});
