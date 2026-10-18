import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import CategoryEditor from './CategoryEditor';

const mocks = vi.hoisted(() => ({
  kind: 'final' as 'standard' | 'final',
  createPrompt: vi.fn(),
  getCategory: vi.fn(),
}));

vi.mock('@/api/categories', () => ({ getCategory: mocks.getCategory }));
vi.mock('@/hooks/usePromptCategories', () => ({
  useCategory: () => ({
    data: { id: 9, name: 'History', kind: mocks.kind, prompts: [] },
    isLoading: false,
  }),
  useUpdateCategory: () => ({ mutateAsync: vi.fn() }),
  useDeleteCategory: () => ({ mutateAsync: vi.fn() }),
  useCreatePrompt: () => ({ mutateAsync: mocks.createPrompt, isPending: false }),
  useUpdatePrompt: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useDeletePrompt: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));

function renderEditor() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <CategoryEditor categoryId={9} />
    </QueryClientProvider>,
  );
}

describe('CategoryEditor kind', () => {
  beforeEach(() => {
    mocks.kind = 'final';
    mocks.createPrompt.mockReset().mockResolvedValue({ id: 1 });
    mocks.getCategory.mockReset().mockResolvedValue({ prompts: [] });
  });

  it('edits one scoreless Final prompt, preserving media controls and storage order one', async () => {
    renderEditor();
    expect(screen.getByRole('heading', { name: 'Final prompt' })).toBeInTheDocument();
    expect(screen.queryByText(/Score:/)).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Category kind')).not.toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: 'Add' })).toHaveLength(1);
    expect(screen.getByLabelText('Question type')).toBeInTheDocument();
    expect(screen.getByLabelText('Answer reveal type')).toBeInTheDocument();

    await userEvent.type(screen.getByLabelText('Question instruction / caption'), 'When?');
    await userEvent.type(screen.getByLabelText('Canonical expected answer'), 'Yesterday');
    await userEvent.click(screen.getByRole('button', { name: 'Add' }));
    expect(mocks.createPrompt).toHaveBeenCalledWith({
      question: 'When?',
      question_type: 'text',
      question_media_asset_id: null,
      answer: 'Yesterday',
      answer_type: 'text',
      answer_media_asset_id: null,
      order: 1,
    });
  });

  it('keeps five scored prompt editors for standard categories', () => {
    mocks.kind = 'standard';
    renderEditor();
    expect(screen.getAllByRole('heading', { name: /Prompt [1-5]/ })).toHaveLength(5);
    expect(screen.getByText('Score: 500')).toBeInTheDocument();
  });
});
