import { render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import TimerBar from './TimerBar';

describe('TimerBar', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-01-01T00:00:00Z'));
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders the remaining seconds', () => {
    const deadline = new Date('2026-01-01T00:00:12Z').toISOString();
    render(<TimerBar deadline={deadline} totalSeconds={30} />);
    expect(screen.getByText('12s')).toBeInTheDocument();
  });

  it('renders nothing if deadline is null', () => {
    const { container } = render(<TimerBar deadline={null} />);
    expect(container.firstChild).toBeNull();
  });
});
