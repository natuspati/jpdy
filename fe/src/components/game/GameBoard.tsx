import type { GameLobbyState } from '@/schemas';
import { canSelectPrompt } from '@/services/game/phaseGuards';

const COLS_CLASS_BY_COUNT: Record<number, string> = {
  1: 'grid-cols-1',
  2: 'grid-cols-2',
  3: 'grid-cols-2 sm:grid-cols-3',
  4: 'grid-cols-2 sm:grid-cols-4',
  5: 'grid-cols-2 sm:grid-cols-3 md:grid-cols-5',
  6: 'grid-cols-2 sm:grid-cols-3 md:grid-cols-6',
};

interface Props {
  state: GameLobbyState;
  currentUserId: number;
  onSelect: (promptId: number) => void;
}

const GameBoard = ({ state, currentUserId, onSelect }: Props) => {
  if (state.categories.length === 0) {
    return <p className="text-slate-400">No categories.</p>;
  }
  // Tailwind JIT requires static class names — pick from a fixed map rather
  // than concatenating into the class string.
  const colsClass = COLS_CLASS_BY_COUNT[Math.min(state.categories.length, 6)];
  return (
    <div className={`grid gap-2 ${colsClass}`}>
      {state.categories.map((cat) => (
        <div key={cat.category_id} className="grid grid-rows-[4.5rem_auto] gap-2">
          <div className="flex min-h-[4.5rem] items-center justify-center overflow-hidden rounded-md bg-(--color-board-bg) p-2 text-center text-sm font-semibold uppercase tracking-wide text-amber-300">
            <span className="line-clamp-2">{cat.name}</span>
          </div>
          <div className="space-y-2">
            {[...cat.prompts]
              .sort((a, b) => a.order - b.order)
              .map((prompt) => {
                const selectable = canSelectPrompt(state, currentUserId, prompt.prompt_id);
                return (
                  <button
                    key={prompt.prompt_id}
                    disabled={!selectable}
                    onClick={() => onSelect(prompt.prompt_id)}
                    className={`h-16 w-full rounded-md text-lg font-bold tabular-nums transition-colors sm:h-20 sm:text-2xl ${
                      prompt.is_selected
                        ? 'bg-(--color-board-tile-spent) text-slate-600'
                        : selectable
                          ? 'bg-(--color-board-tile) text-amber-300 hover:bg-amber-400 hover:text-slate-900'
                          : 'bg-(--color-board-tile) text-amber-300 opacity-90'
                    }`}
                  >
                    {prompt.is_selected ? '—' : prompt.score_value}
                  </button>
                );
              })}
          </div>
        </div>
      ))}
    </div>
  );
};

export default GameBoard;
