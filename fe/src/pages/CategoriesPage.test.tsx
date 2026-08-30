import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import CategoriesPage from './CategoriesPage';

const { createCategory } = vi.hoisted(() => ({
  createCategory: vi.fn(),
}));

vi.mock('@/hooks/usePromptCategories', () => ({
  useMyCategories: () => ({ data: { contents: [] }, isLoading: false }),
  useCreateCategory: () => ({ isPending: false, mutateAsync: createCategory }),
}));

describe('CategoriesPage', () => {
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
});
