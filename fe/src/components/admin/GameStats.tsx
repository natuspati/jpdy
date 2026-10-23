import { useCallback } from 'react';

import Badge from '@/components/ui/Badge';
import Card from '@/components/ui/Card';
import Spinner from '@/components/ui/Spinner';
import { useCategoryStats, useGameStats } from '@/hooks/useAdmin';
import { useInfiniteScroll } from '@/hooks/useInfiniteScroll';
import AdminSection from './AdminSection';

const Tile = ({ label, value }: { label: string; value: number | undefined }) => (
  <Card className="p-3 text-center">
    <p className="text-2xl font-bold tabular-nums text-amber-300">{value ?? '-'}</p>
    <p className="text-xs text-slate-400">{label}</p>
  </Card>
);

const GameStats = () => {
  const stats = useGameStats();
  const categories = useCategoryStats();
  const { fetchNextPage, hasNextPage, isFetchingNextPage } = categories;
  const loadMore = useCallback(() => void fetchNextPage(), [fetchNextPage]);
  const sentinelRef = useInfiniteScroll(loadMore, hasNextPage && !isFetchingNextPage);
  const rows = categories.data ?? [];
  const maxPlayed = Math.max(1, ...rows.map((row) => row.lobbies_played));

  return (
    <AdminSection title="Game stats">
      <div className="space-y-3 p-3">
        {stats.isError ? <p className="text-rose-400">Stats are unavailable.</p> : null}
        <div className="grid grid-cols-3 gap-3">
          <Tile label="Active lobbies" value={stats.data?.active_lobbies} />
          <Tile label="Active players" value={stats.data?.active_players} />
          <Tile label="Completed lobbies" value={stats.data?.completed_lobbies} />
        </div>
        <h3 className="font-semibold text-slate-100">Popular categories</h3>
        {categories.isLoading ? (
          <div className="flex justify-center">
            <Spinner />
          </div>
        ) : categories.isError ? (
          <p className="text-rose-400">Category stats are unavailable.</p>
        ) : (
          <table className="min-w-full text-left text-sm">
            <thead className="text-xs uppercase tracking-wide text-slate-400">
              <tr>
                <th className="py-1 pr-2">Category</th>
                <th className="w-1/2 py-1 pr-2">Lobbies</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {rows.length === 0 ? (
                <tr>
                  <td colSpan={2} className="py-3 text-center text-slate-400">
                    No games played yet.
                  </td>
                </tr>
              ) : null}
              {rows.map((row) => (
                <tr key={row.id}>
                  <td className="max-w-40 py-2 pr-2 text-slate-100">
                    <span className="flex items-center gap-2">
                      <span className="truncate">{row.name}</span>
                      {row.kind === 'final' ? <Badge tone="info">final</Badge> : null}
                    </span>
                  </td>
                  <td className="py-2 pr-2">
                    <div className="flex items-center gap-2">
                      <div className="h-2 flex-1 rounded bg-slate-800">
                        <div
                          className="h-2 rounded bg-amber-400"
                          style={{ width: `${(row.lobbies_played / maxPlayed) * 100}%` }}
                        />
                      </div>
                      <span className="w-8 text-right tabular-nums text-slate-300">
                        {row.lobbies_played}
                      </span>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {isFetchingNextPage ? (
          <div className="flex justify-center">
            <Spinner />
          </div>
        ) : null}
        <div ref={sentinelRef} aria-hidden className="h-px" />
      </div>
    </AdminSection>
  );
};

export default GameStats;
