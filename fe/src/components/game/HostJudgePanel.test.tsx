import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import HostJudgePanel from './HostJudgePanel';

describe('HostJudgePanel', () => {
  it('shows the answering player and expected answer', () => {
    render(<HostJudgePanel answeringPlayerName="Alex" expectedAnswer="kangaroo" />);
    expect(screen.getByText('Alex')).toBeInTheDocument();
    expect(screen.getByText('kangaroo')).toBeInTheDocument();
  });

  it('keeps judging controls out of the answer-key guidance panel', () => {
    render(<HostJudgePanel answeringPlayerName="Alex" />);
    expect(
      screen.queryByRole('button', { name: /accept|decline|correct|wrong/i }),
    ).not.toBeInTheDocument();
  });

  it('does not display an expected-answer section without host-private data', () => {
    render(<HostJudgePanel answeringPlayerName="Alex" />);
    expect(screen.queryByText('Answer key')).not.toBeInTheDocument();
  });
});
