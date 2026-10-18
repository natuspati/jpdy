import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import CategoriesPage from './CategoriesPage';

const { createCategory, categoryData } = vi.hoisted(() => ({
  createCategory: vi.fn(),
  categoryData: {
    contents: [] as {
      id: number;
      name: string;
      kind: 'standard' | 'final';
      prompts: { order: number }[];
    }[],
  },
}));

vi.mock('@/hooks/usePromptCategories', () => ({
  useMyCategories: () => ({ data: categoryData, isLoading: false }),
  useCreateCategory: () => ({ isPending: false, mutateAsync: createCategory }),
}));

describe('CategoriesPage', () => {
  beforeEach(() => {
    categoryData.contents = [];
    createCategory.mockReset().mockResolvedValue({ id: 42 });
  });

  it('opens the new category dialog from the labelled plus button', () => {
    render(
      <MemoryRouter>
        <CategoriesPage />
      </MemoryRouter>,
    );

    const newCategoryButton = screen.getByRole('button', { name: 'New category' });
    expect(newCategoryButton).toHaveAttribute('title', 'New category');
    expect(screen.getByRole('tooltip', { name: 'New category' })).toBeInTheDocument();

    fireEvent.click(newCategoryButton);
    expect(screen.getByRole('dialog')).toHaveTextContent('New category');
  });

  it('creates Final categories with a creation-time kind choice', async () => {
    render(
      <MemoryRouter>
        <CategoriesPage />
      </MemoryRouter>,
    );
    await userEvent.click(screen.getByRole('button', { name: 'New category' }));
    await userEvent.type(screen.getByLabelText('Name'), 'Final history');
    await userEvent.selectOptions(screen.getByLabelText('Category kind'), 'final');
    await userEvent.click(screen.getByRole('button', { name: 'Create' }));
    expect(createCategory).toHaveBeenCalledWith({ name: 'Final history', kind: 'final' });
  });

  it('shows a one-prompt Final as ready and keeps an incomplete standard category a draft', () => {
    categoryData.contents = [
      { id: 1, name: 'Final history', kind: 'final', prompts: [{ order: 1 }] },
      { id: 2, name: 'History', kind: 'standard', prompts: [{ order: 1 }] },
      { id: 3, name: 'Invalid final', kind: 'final', prompts: [{ order: 2 }] },
    ];
    render(
      <MemoryRouter>
        <CategoriesPage />
      </MemoryRouter>,
    );
    expect(screen.getAllByText('1 / 1 prompts')).toHaveLength(2);
    expect(screen.getByText('1 / 5 prompts')).toBeInTheDocument();
    expect(screen.getAllByText('Ready')).toHaveLength(1);
    expect(screen.getAllByText('Draft')).toHaveLength(2);
    expect(screen.getAllByText('Final')).toHaveLength(2);
  });
});
