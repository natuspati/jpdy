import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { formatLocalDateTime } from '@/utils/formatDateTime';
import CategoriesPage from './CategoriesPage';

const { createCategory, myCategories, categoryData } = vi.hoisted(() => ({
  createCategory: vi.fn(),
  myCategories: vi.fn(),
  categoryData: {
    contents: [] as {
      id: number;
      name: string;
      kind: 'standard' | 'final';
      updated_at: string;
      prompts: { order: number }[];
    }[],
  },
}));

vi.mock('@/hooks/usePromptCategories', () => ({
  useMyCategories: (filters: unknown) => {
    myCategories(filters);
    return {
      data: categoryData.contents,
      isLoading: false,
      hasNextPage: false,
      isFetchingNextPage: false,
      fetchNextPage: vi.fn(),
    };
  },
  useCreateCategory: () => ({ isPending: false, mutateAsync: createCategory }),
}));

const renderPage = () =>
  render(
    <MemoryRouter>
      <CategoriesPage />
    </MemoryRouter>,
  );

describe('CategoriesPage', () => {
  beforeEach(() => {
    categoryData.contents = [];
    myCategories.mockClear();
    createCategory.mockReset().mockResolvedValue({ id: 42 });
  });

  it('opens the new category dialog from the labelled plus button', () => {
    renderPage();

    const newCategoryButton = screen.getByRole('button', { name: 'New category' });
    expect(newCategoryButton).toHaveAttribute('title', 'New category');
    expect(screen.getByRole('tooltip', { name: 'New category' })).toBeInTheDocument();

    fireEvent.click(newCategoryButton);
    expect(screen.getByRole('dialog')).toHaveTextContent('New category');
  });

  it('creates Final categories with a creation-time kind choice', async () => {
    renderPage();
    await userEvent.click(screen.getByRole('button', { name: 'New category' }));
    await userEvent.type(screen.getByLabelText('Name'), 'Final history');
    await userEvent.selectOptions(screen.getByLabelText('Category kind'), 'final');
    await userEvent.click(screen.getByRole('button', { name: 'Create' }));
    expect(createCategory).toHaveBeenCalledWith({ name: 'Final history', kind: 'final' });
  });

  it('shows x/y pills, the kind and the updated date, and highlights only complete cards', () => {
    const updatedAt = '2026-09-02T10:30:00Z';
    categoryData.contents = [
      {
        id: 1,
        name: 'Final history',
        kind: 'final',
        updated_at: updatedAt,
        prompts: [{ order: 1 }],
      },
      { id: 2, name: 'History', kind: 'standard', updated_at: updatedAt, prompts: [{ order: 1 }] },
      {
        id: 3,
        name: 'Invalid final',
        kind: 'final',
        updated_at: updatedAt,
        prompts: [{ order: 2 }],
      },
    ];
    renderPage();

    expect(screen.getAllByText('1/1')).toHaveLength(2);
    expect(screen.getByText('1/5')).toBeInTheDocument();
    expect(screen.queryByText('Ready')).not.toBeInTheDocument();
    expect(screen.queryByText('Draft')).not.toBeInTheDocument();
    expect(screen.getAllByText('Final', { selector: 'span' })).toHaveLength(2);
    expect(screen.getAllByText('Standard', { selector: 'span' })).toHaveLength(1);
    expect(screen.getAllByText(`Updated ${formatLocalDateTime(updatedAt)}`)).toHaveLength(3);

    const card = (name: string) => screen.getByRole('link', { name }).closest('[data-complete]');
    expect(card('Final history')).toHaveAttribute('data-complete', 'true');
    expect(card('History')).toHaveAttribute('data-complete', 'false');
    expect(card('Invalid final')).toHaveAttribute('data-complete', 'false');
  });

  it('shows the full name as a tooltip on a truncated title', () => {
    categoryData.contents = [
      {
        id: 1,
        name: 'A very long category name',
        kind: 'standard',
        updated_at: '2026-09-02T10:30:00Z',
        prompts: [],
      },
    ];
    renderPage();
    expect(screen.getByRole('link', { name: 'A very long category name' })).toHaveAttribute(
      'title',
      'A very long category name',
    );
  });

  it('loads with no filters, then sends readiness, type, sort and a debounced search', async () => {
    renderPage();
    expect(myCategories).toHaveBeenLastCalledWith({
      is_complete: undefined,
      kind: undefined,
      sort: 'updated_desc',
      name: undefined,
    });

    const bar = screen.getAllByLabelText('Completeness')[0];
    await userEvent.selectOptions(bar, 'complete');
    await userEvent.selectOptions(screen.getAllByLabelText('Type')[0], 'final');
    await userEvent.selectOptions(screen.getAllByLabelText('Sort')[0], 'name_asc');
    await userEvent.type(screen.getByLabelText('Search categories'), 'hist');

    await waitFor(() =>
      expect(myCategories).toHaveBeenLastCalledWith({
        is_complete: true,
        kind: 'final',
        sort: 'name_asc',
        name: 'hist',
      }),
    );
    expect(myCategories).not.toHaveBeenCalledWith(expect.objectContaining({ name: 'hi' }));
  });

  it('maps Incomplete to is_complete=false', async () => {
    renderPage();
    await userEvent.selectOptions(screen.getAllByLabelText('Completeness')[0], 'incomplete');
    expect(myCategories).toHaveBeenLastCalledWith(expect.objectContaining({ is_complete: false }));
  });

  it('collapses the selects into a Filters sheet with an active count', async () => {
    renderPage();
    await userEvent.click(screen.getByRole('button', { name: 'Filters' }));
    const sheet = screen.getByRole('dialog');
    await userEvent.selectOptions(within(sheet).getByLabelText('Type'), 'standard');
    await userEvent.selectOptions(within(sheet).getByLabelText('Sort'), 'name_desc');
    await userEvent.click(within(sheet).getByRole('button', { name: 'Done' }));

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Filters (2)' })).toBeInTheDocument();
    expect(myCategories).toHaveBeenLastCalledWith(
      expect.objectContaining({ kind: 'standard', sort: 'name_desc' }),
    );
  });

  it('tells a filtered empty list apart from having no categories', async () => {
    renderPage();
    expect(screen.getByText('No categories yet.')).toBeInTheDocument();
    await userEvent.selectOptions(screen.getAllByLabelText('Type')[0], 'final');
    expect(screen.getByText('No categories match your filters.')).toBeInTheDocument();
  });
});
