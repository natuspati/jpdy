import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import BuzzButton from './BuzzButton';

describe('BuzzButton', () => {
  it('is disabled when not enabled', () => {
    const onBuzz = vi.fn();
    render(<BuzzButton enabled={false} disabledReason="Already attempted." onBuzz={onBuzz} />);
    expect(screen.getByRole('button', { name: /buzz/i })).toBeDisabled();
    expect(screen.getByText('Already attempted.')).toBeInTheDocument();
  });

  it('fires onBuzz when enabled', async () => {
    const onBuzz = vi.fn();
    render(<BuzzButton enabled={true} onBuzz={onBuzz} />);
    await userEvent.click(screen.getByRole('button', { name: /buzz/i }));
    expect(onBuzz).toHaveBeenCalledTimes(1);
  });
});
