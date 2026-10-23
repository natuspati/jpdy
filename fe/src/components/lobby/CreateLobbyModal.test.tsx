import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { formatLocalDateTime } from '@/utils/formatDateTime';
import CreateLobbyModal from './CreateLobbyModal';

const mocks = vi.hoisted(() => ({
  createLobby: vi.fn(),
  updateLobby: vi.fn(),
  availableCategories: vi.fn(),
}));

const categories = Array.from({ length: 7 }, (_, index) => ({
  id: index + 1,
  name: `Cat ${index + 1}`,
  kind: 'standard',
  owner_id: index === 0 ? 1 : 2,
  updated_at: '2026-09-01T10:00:00Z',
  prompts: Array.from({ length: 5 }, (_, order) => ({ id: index * 10 + order })),
}));

vi.mock('@/hooks/usePromptCategories', () => ({
  useAvailableCategories: (kind: string, name?: string) => {
    mocks.availableCategories(kind, name);
    return {
      data: {
        contents:
          kind === 'final'
            ? [{ id: 100, name: 'Final history', kind: 'final', prompts: [{ id: 1000 }] }]
            : categories.filter((category) => !name || category.name.includes(name)),
      },
      isLoading: false,
    };
  },
}));

vi.mock('@/hooks/useAuth', () => ({ useAuth: () => ({ userId: 1 }) }));

vi.mock('@/hooks/useLobbies', () => ({
  useCreateLobby: () => ({ mutateAsync: mocks.createLobby, isPending: false }),
  useUpdateLobby: () => ({ mutateAsync: mocks.updateLobby, isPending: false }),
}));

const renderModal = () =>
  render(
    <MemoryRouter>
      <CreateLobbyModal open onClose={vi.fn()} />
    </MemoryRouter>,
  );

const pick = (n: number, round: number) =>
  userEvent.click(screen.getByRole('button', { name: `Add Cat ${n} to round ${round}` }));
const catButton = (n: number, round: number) =>
  screen.getByRole('button', { name: `Add Cat ${n} to round ${round}` });

describe('CreateLobbyModal rounds editor', () => {
  beforeEach(() => {
    mocks.createLobby.mockReset().mockResolvedValue({ id: 42 });
    mocks.updateLobby.mockReset().mockResolvedValue({});
  });

  it('starts with one round and keeps create disabled until every round has a category', async () => {
    renderModal();
    const create = screen.getByRole('button', { name: 'Create & open' });
    expect(screen.getByRole('button', { name: 'Round 1' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Remove round/ })).not.toBeInTheDocument();
    expect(create).toBeDisabled();

    await pick(1, 1);
    expect(create).toBeEnabled();

    await userEvent.click(screen.getByRole('button', { name: 'Add round' }));
    expect(screen.getByText(/values ×2/)).toBeInTheDocument();
    expect(create).toBeDisabled();
  });

  it('caps rounds at three and allows removing down to one', async () => {
    renderModal();
    const add = screen.getByRole('button', { name: 'Add round' });
    await userEvent.click(add);
    await userEvent.click(add);
    expect(add).toBeDisabled();
    expect(screen.getByText(/values ×4/)).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Remove round 3' }));
    await userEvent.click(screen.getByRole('button', { name: 'Remove round 2' }));
    expect(add).toBeEnabled();
    expect(screen.queryByRole('button', { name: /Remove round/ })).not.toBeInTheDocument();
  });

  it('disables a picked category everywhere, caps five per round and frees it on removal', async () => {
    renderModal();
    await pick(1, 1);
    expect(catButton(1, 1)).toBeDisabled();

    await userEvent.click(screen.getByRole('button', { name: 'Add round' }));
    expect(catButton(1, 2)).toBeDisabled();
    expect(catButton(6, 2)).toBeEnabled();

    await userEvent.click(screen.getByRole('button', { name: 'Round 1' }));
    for (const n of [2, 3, 4, 5]) await pick(n, 1);
    expect(catButton(6, 1)).toBeDisabled();

    await userEvent.click(screen.getByRole('button', { name: 'Remove Cat 1 from round 1' }));
    expect(catButton(1, 1)).toBeEnabled();
    expect(catButton(6, 1)).toBeEnabled();
  });

  it('omits the betting count when blank and sends it when set', async () => {
    renderModal();
    await pick(1, 1);
    await userEvent.click(screen.getByRole('button', { name: 'Create & open' }));
    expect(mocks.updateLobby).toHaveBeenNthCalledWith(1, {
      id: 42,
      payload: { rounds: [[1]], final_category_id: null },
    });

    mocks.updateLobby.mockClear();
    await userEvent.type(screen.getByLabelText('Betting prompts in each round'), '3');
    await userEvent.click(screen.getByRole('button', { name: 'Create & open' }));
    expect(mocks.updateLobby).toHaveBeenNthCalledWith(1, {
      id: 42,
      payload: { rounds: [[1]], final_category_id: null, betting_prompt_count: 3 },
    });
  });

  it('disables create for an out-of-range betting count', async () => {
    renderModal();
    await pick(1, 1);
    await userEvent.type(screen.getByLabelText('Betting prompts in each round'), '26');

    expect(screen.getByRole('button', { name: 'Create & open' })).toBeDisabled();
  });

  it('previews betting prompts per round for the default and a custom count', async () => {
    renderModal();
    await pick(1, 1);
    expect(screen.getByText(/Round 1: 0 of 5 prompts/)).toBeInTheDocument();

    for (const n of [2, 3]) await pick(n, 1);
    expect(screen.getByText(/Round 1: 1 of 15 prompts/)).toBeInTheDocument();

    await userEvent.type(screen.getByLabelText('Betting prompts in each round'), '4');
    expect(screen.getByText(/Round 1: 4 of 15 prompts/)).toBeInTheDocument();

    await userEvent.clear(screen.getByLabelText('Betting prompts in each round'));
    await userEvent.type(screen.getByLabelText('Betting prompts in each round'), '9');
    await userEvent.click(screen.getByRole('button', { name: 'Remove Cat 1 from round 1' }));
    await userEvent.click(screen.getByRole('button', { name: 'Remove Cat 3 from round 1' }));
    expect(screen.getByText(/Round 1: 5 of 5 prompts/)).toBeInTheDocument();
  });

  it('sends the rounds payload and then promotes the lobby', async () => {
    renderModal();
    await pick(1, 1);
    await pick(2, 1);
    await userEvent.click(screen.getByRole('button', { name: 'Add round' }));
    await pick(3, 2);

    await userEvent.click(screen.getByRole('button', { name: 'Create & open' }));

    expect(mocks.updateLobby).toHaveBeenNthCalledWith(1, {
      id: 42,
      payload: { rounds: [[1, 2], [3]], final_category_id: null },
    });
    expect(mocks.updateLobby).toHaveBeenNthCalledWith(2, {
      id: 42,
      payload: { state: 'waiting_start' },
    });
  });

  it('keeps the optional final separate from three normal rounds and saves it before opening', async () => {
    renderModal();
    expect(mocks.availableCategories).toHaveBeenCalledWith('standard', '');
    expect(mocks.availableCategories).toHaveBeenCalledWith('final', undefined);
    expect(screen.queryByRole('button', { name: /Final history/ })).not.toBeInTheDocument();
    expect(screen.queryByRole('option', { name: 'Cat 1' })).not.toBeInTheDocument();

    await pick(1, 1);
    await userEvent.click(screen.getByRole('button', { name: 'Add round' }));
    await pick(2, 2);
    await userEvent.click(screen.getByRole('button', { name: 'Add round' }));
    await pick(3, 3);
    await userEvent.selectOptions(screen.getByLabelText('Final category (optional)'), '100');
    await userEvent.click(screen.getByRole('button', { name: 'Create & open' }));

    expect(mocks.updateLobby).toHaveBeenNthCalledWith(1, {
      id: 42,
      payload: { rounds: [[1], [2], [3]], final_category_id: 100 },
    });
    expect(mocks.updateLobby).toHaveBeenNthCalledWith(2, {
      id: 42,
      payload: { state: 'waiting_start' },
    });
  });

  it('allows removing the optional final without changing normal selections', async () => {
    renderModal();
    await pick(1, 1);
    await userEvent.selectOptions(screen.getByLabelText('Final category (optional)'), '100');
    await userEvent.selectOptions(screen.getByLabelText('Final category (optional)'), '');
    await userEvent.click(screen.getByRole('button', { name: 'Create & open' }));
    expect(mocks.updateLobby).toHaveBeenNthCalledWith(1, {
      id: 42,
      payload: { rounds: [[1]], final_category_id: null },
    });
  });

  it("marks the viewer's own categories and shows prompt count and updated date", () => {
    renderModal();
    expect(screen.getAllByText('Yours')).toHaveLength(1);
    expect(catButton(1, 1)).toHaveTextContent('Yours');
    expect(catButton(2, 1)).not.toHaveTextContent('Yours');
    expect(catButton(1, 1)).toHaveTextContent('5 prompts');
    expect(catButton(1, 1)).toHaveTextContent(
      `Updated ${formatLocalDateTime(categories[0].updated_at)}`,
    );
  });

  it('searches by a debounced name and keeps picked categories across searches', async () => {
    renderModal();
    await pick(1, 1);

    await userEvent.type(screen.getByLabelText('Search categories'), 'Cat 2');
    await waitFor(() =>
      expect(mocks.availableCategories).toHaveBeenCalledWith('standard', 'Cat 2'),
    );
    expect(mocks.availableCategories).not.toHaveBeenCalledWith('standard', 'Cat');
    expect(screen.queryByRole('button', { name: 'Add Cat 1 to round 1' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Remove Cat 1 from round 1' })).toBeInTheDocument();

    await pick(2, 1);
    await userEvent.click(screen.getByRole('button', { name: 'Create & open' }));
    expect(mocks.updateLobby).toHaveBeenNthCalledWith(1, {
      id: 42,
      payload: { rounds: [[1, 2]], final_category_id: null },
    });
  });

  it('says so when a search matches nothing', async () => {
    renderModal();
    await userEvent.type(screen.getByLabelText('Search categories'), 'zzz');
    expect(await screen.findByText('No ready categories match your search.')).toBeInTheDocument();
  });
});
