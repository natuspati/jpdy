import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { buildGameState } from '@/test/fixtures/gameState';
import PromptStage from './PromptStage';

describe('PromptStage', () => {
  it('does not render an answer before reveal', () => {
    const prompt = buildGameState().categories[0].prompts[0];
    render(<PromptStage prompt={prompt} />);

    expect(screen.queryByText(/correct answer/i)).not.toBeInTheDocument();
    expect(screen.queryByText('Category 1 A1')).not.toBeInTheDocument();
  });

  it('renders public answer and resolution during reveal', () => {
    const prompt = buildGameState().categories[0].prompts[0];
    render(<PromptStage prompt={prompt} answer="Category 1 A1" resolution="correct" />);

    expect(screen.getByText('Correct answer')).toBeInTheDocument();
    expect(screen.getByText('Category 1 A1')).toBeInTheDocument();
    expect(screen.getByText('Correct response.')).toBeInTheDocument();
  });
});
