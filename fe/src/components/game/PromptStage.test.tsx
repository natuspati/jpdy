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

  it('renders question media during clue and withholds answer media', () => {
    const prompt = {
      ...buildGameState().categories[0].prompts[0],
      question_type: 'image' as const,
      question_media: {
        asset_id: 1,
        url: '/media/question.png',
        mime_type: 'image/png',
        filename: 'question.png',
      },
    };
    render(<PromptStage prompt={prompt} />);

    expect(screen.getByAltText('Q1')).toHaveAttribute('src', '/media/question.png');
    expect(screen.queryByAltText('Answer: Correct answer')).not.toBeInTheDocument();
  });

  it('renders public answer and resolution during reveal', () => {
    const prompt = buildGameState().categories[0].prompts[0];
    render(<PromptStage prompt={prompt} answer="Category 1 A1" resolution="correct" />);

    expect(screen.getByText('Correct answer')).toBeInTheDocument();
    expect(screen.getByText('Category 1 A1')).toBeInTheDocument();
    expect(screen.getByText('Correct response.')).toBeInTheDocument();
  });

  it('renders answer media only during answer reveal', () => {
    const prompt = {
      ...buildGameState().categories[0].prompts[0],
      question_type: 'image' as const,
      question_media: {
        asset_id: 1,
        url: '/media/question.png',
        mime_type: 'image/png',
        filename: 'question.png',
      },
    };
    render(
      <PromptStage
        prompt={prompt}
        answer="Correct answer"
        answerType="image"
        answerMedia={{
          asset_id: 2,
          url: '/media/answer.png',
          mime_type: 'image/png',
          filename: 'answer.png',
        }}
      />,
    );

    expect(screen.getByAltText('Q1')).toHaveAttribute('src', '/media/question.png');
    expect(screen.getByAltText('Answer: Correct answer')).toHaveAttribute(
      'src',
      '/media/answer.png',
    );
  });
});
