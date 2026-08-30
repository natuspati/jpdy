import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import HostJudgePanel from './HostJudgePanel';

describe('HostJudgePanel', () => {
  it('shows spoken-answer copy and expected answer', () => {
    render(
      <HostJudgePanel
        answeringPlayerName="Alex"
        expectedAnswer="kangaroo"
        onJudge={() => undefined}
      />,
    );
    expect(screen.getByText(/listen to Alex's spoken answer/i)).toBeInTheDocument();
    expect(screen.getByText('kangaroo')).toBeInTheDocument();
  });

  it('emits judge with the correct flag', async () => {
    const onJudge = vi.fn();
    render(<HostJudgePanel answeringPlayerName="Alex" onJudge={onJudge} />);
    await userEvent.click(screen.getByRole('button', { name: /correct/i }));
    expect(onJudge).toHaveBeenCalledWith(true);
    await userEvent.click(screen.getByRole('button', { name: /wrong/i }));
    expect(onJudge).toHaveBeenCalledWith(false);
  });

  it('does not display an expected-answer section without host-private data', () => {
    render(<HostJudgePanel answeringPlayerName="Alex" onJudge={() => undefined} />);
    expect(screen.queryByText('Answer key')).not.toBeInTheDocument();
  });
});
