import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import HostJudgePanel from './HostJudgePanel';

describe('HostJudgePanel', () => {
  it('shows the submitted answer and expected answer', () => {
    render(
      <HostJudgePanel
        submittedAnswer="koala"
        expectedAnswer="kangaroo"
        onJudge={() => undefined}
      />,
    );
    expect(screen.getByText('koala')).toBeInTheDocument();
    expect(screen.getByText('kangaroo')).toBeInTheDocument();
  });

  it('emits judge with the correct flag', async () => {
    const onJudge = vi.fn();
    render(<HostJudgePanel submittedAnswer="a" onJudge={onJudge} />);
    await userEvent.click(screen.getByRole('button', { name: /correct/i }));
    expect(onJudge).toHaveBeenCalledWith(true);
    await userEvent.click(screen.getByRole('button', { name: /wrong/i }));
    expect(onJudge).toHaveBeenCalledWith(false);
  });
});
