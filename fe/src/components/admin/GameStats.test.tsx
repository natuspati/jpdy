import { render, screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import GameStats from './GameStats';

vi.mock('@/hooks/useAdmin', () => ({
  useGameStats: () => ({
    data: { active_lobbies: 3, completed_lobbies: 21 },
    isError: false,
  }),
  useServerStatus: () => ({ data: { backend: { connected_sockets: 8 } } }),
  useCategoryStats: () => ({
    data: [
      { id: 1, name: 'Space', kind: 'standard', lobbies_played: 10 },
      { id: 2, name: 'Finale', kind: 'final', lobbies_played: 5 },
    ],
    isLoading: false,
    isError: false,
    hasNextPage: false,
    isFetchingNextPage: false,
    fetchNextPage: vi.fn(),
  }),
}));

describe('GameStats', () => {
  it('shows the tiles and scales category bars to the most played one', () => {
    const { container } = render(<GameStats />);

    expect(screen.getByText('Active lobbies').previousElementSibling).toHaveTextContent('3');
    expect(screen.getByText('Active players').previousElementSibling).toHaveTextContent('8');
    expect(screen.getByText('Completed lobbies').previousElementSibling).toHaveTextContent('21');

    const finale = screen.getByText('Finale').closest('tr');
    if (!finale) throw new Error('Finale row missing');
    expect(within(finale).getByText('final')).toBeInTheDocument();
    const widths = [...container.querySelectorAll<HTMLElement>('tbody [style]')].map(
      (bar) => bar.style.width,
    );
    expect(widths).toEqual(['100%', '50%']);
  });
});
