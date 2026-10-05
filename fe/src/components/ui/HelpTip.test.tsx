import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import HelpTip from './HelpTip';

describe('HelpTip', () => {
  it('describes its button, opens on tap, and closes on outside tap or Escape', () => {
    render(<HelpTip text="Short help" />);

    const button = screen.getByRole('button', { name: 'More info' });
    const tooltip = screen.getByRole('tooltip', { hidden: true });
    expect(button).toHaveAccessibleDescription('Short help');
    expect(tooltip).toHaveClass('invisible');

    fireEvent.click(button);
    expect(tooltip).toHaveClass('visible');
    expect(button).toHaveAttribute('aria-expanded', 'true');

    fireEvent.pointerDown(document.body);
    expect(tooltip).toHaveClass('invisible');

    fireEvent.click(button);
    fireEvent.keyDown(button, { key: 'Escape' });
    expect(tooltip).toHaveClass('invisible');
  });
});
