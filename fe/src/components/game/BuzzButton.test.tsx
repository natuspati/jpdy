import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import BuzzButton from './BuzzButton';

describe('BuzzButton', () => {
  it('is disabled when not enabled', () => {
    const onBuzz = vi.fn();
    render(<BuzzButton enabled={false} disabledReason="Already attempted." onBuzz={onBuzz} />);
    const buzzer = screen.getByRole('button', { name: /buzz/i });
    expect(buzzer).toBeDisabled();
    expect(buzzer).toHaveClass('rounded-full', 'size-36', 'translate-y-2');
    expect(screen.getByText('Already attempted.')).toBeInTheDocument();
  });

  it('fires onBuzz when enabled', async () => {
    const onBuzz = vi.fn();
    render(<BuzzButton enabled={true} onBuzz={onBuzz} />);
    const buzzer = screen.getByRole('button', { name: /buzz/i });
    expect(buzzer).toHaveClass('rounded-full', 'size-36', 'active:translate-y-2');
    await userEvent.click(buzzer);
    expect(onBuzz).toHaveBeenCalledTimes(1);
  });
});
