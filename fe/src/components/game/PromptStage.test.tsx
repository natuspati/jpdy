import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { buildGameState } from '@/test/fixtures/gameState';
import PromptStage from './PromptStage';

describe('PromptStage', () => {
  it('does not render an answer before reveal', () => {
    const prompt = buildGameState().categories[0].prompts[0];
    render(<PromptStage prompt={prompt} />);

    expect(screen.queryByText('Category 1 A1')).not.toBeInTheDocument();
    expect(screen.getByLabelText('100 points')).toBeInTheDocument();
  });

  it('renders question media during clue and places media below the question text', () => {
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
    expect(screen.getByAltText('Q1')).toHaveClass('object-contain');
    expect(screen.getByTestId('prompt-stage-content')).toHaveClass('justify-start');
  });

  it('replaces question content with a green answer-only reveal for correct responses', () => {
    const prompt = buildGameState().categories[0].prompts[0];
    render(<PromptStage prompt={prompt} answer="Category 1 A1" resolution="correct" />);

    expect(screen.getByText('Category 1 A1')).toBeInTheDocument();
    expect(screen.queryByText('Q1')).not.toBeInTheDocument();
    expect(screen.queryByText(/correct answer|correct response/i)).not.toBeInTheDocument();
    expect(screen.getByLabelText('Prompt stage')).toHaveAttribute('data-resolution', 'correct');
    expect(screen.getByLabelText('Prompt stage')).toHaveClass('border-emerald-400/70');
  });

  it('replaces question media with answer media during answer reveal', () => {
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

    expect(screen.queryByAltText('Q1')).not.toBeInTheDocument();
    expect(screen.getByAltText('Answer: Correct answer')).toHaveAttribute(
      'src',
      '/media/answer.png',
    );
  });

  it.each(['unanswered', 'expired'] as const)(
    'uses the red reveal treatment for %s answers',
    (resolution) => {
      const prompt = buildGameState().categories[0].prompts[0];
      render(<PromptStage prompt={prompt} answer="Category 1 A1" resolution={resolution} />);

      expect(screen.getByLabelText('Prompt stage')).toHaveClass('border-rose-400/70');
    },
  );
});
