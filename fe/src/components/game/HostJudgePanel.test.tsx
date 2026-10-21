import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import HostJudgePanel from './HostJudgePanel';

describe('HostJudgePanel', () => {
  it('shows the expected answer', () => {
    render(<HostJudgePanel expectedAnswer="kangaroo" />);
    expect(screen.getByText('kangaroo')).toBeInTheDocument();
  });

  it('keeps judging controls out of the answer-key guidance panel', () => {
    render(<HostJudgePanel />);
    expect(
      screen.queryByRole('button', { name: /accept|decline|correct|wrong/i }),
    ).not.toBeInTheDocument();
  });

  it('does not display an expected-answer section without host-private data', () => {
    render(<HostJudgePanel />);
    expect(screen.queryByText('Answer key')).not.toBeInTheDocument();
  });
});
