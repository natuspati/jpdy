import type { GameLobbyState } from '@/schemas';
import { canSelectPrompt } from '@/services/game/phaseGuards';

const COLS_CLASS_BY_COUNT: Record<number, string> = {
  1: 'grid-cols-1',
  2: 'grid-cols-2',
  3: 'grid-cols-3',
  4: 'grid-cols-4',
  5: 'grid-cols-5',
  6: 'grid-cols-2 sm:grid-cols-3 md:grid-cols-6',
};

interface Props {
  state: GameLobbyState;
  currentUserId: number;
  onSelect: (promptId: number) => void;
  /** Tile that was just picked: flashes (showing its value) instead of reading as spent. */
  flashPromptId?: number | null;
}

const GameBoard = ({ state, currentUserId, onSelect, flashPromptId = null }: Props) => {
  // `state.categories` holds every round (so media can preload); the board shows only this one.
  const categories = state.categories.filter(
    (cat) => cat.kind !== 'final' && cat.round_number === state.current_round,
  );
  if (categories.length === 0) {
    return <p className="text-slate-400">No categories.</p>;
  }
  // Tailwind JIT requires static class names — pick from a fixed map rather
  // than concatenating into the class string.
  const colsClass = COLS_CLASS_BY_COUNT[Math.min(categories.length, 6)];
  // Up to 5 categories fit side by side on phones, so shrink the tiles; 6+ keep the roomy layout.
  const compact = categories.length <= 5;
  return (
    <div className={`grid ${compact ? 'gap-1 sm:gap-2' : 'gap-2'} ${colsClass}`}>
      {categories.map((cat) => (
        <div
          key={cat.category_id}
          className={`grid gap-1 sm:gap-2 ${compact ? 'grid-rows-[3rem_auto] sm:grid-rows-[4.5rem_auto]' : 'grid-rows-[4.5rem_auto]'}`}
        >
          <div
            className={`flex min-w-0 items-center justify-center overflow-hidden rounded-md bg-(--color-board-bg) text-center font-semibold uppercase tracking-wide text-amber-300 ${
              compact
                ? 'min-h-12 p-1 text-[10px] sm:min-h-[4.5rem] sm:p-2 sm:text-sm'
                : 'min-h-[4.5rem] p-2 text-sm'
            }`}
          >
            <span className="line-clamp-2 min-w-0 break-words">{cat.name}</span>
          </div>
          <div className="space-y-1 sm:space-y-2">
            {[...cat.prompts]
              .sort((a, b) => a.order - b.order)
              .map((prompt) => {
                const selectable = canSelectPrompt(state, currentUserId, prompt.prompt_id);
                const flashing = prompt.prompt_id === flashPromptId;
                return (
                  <button
                    key={prompt.prompt_id}
                    disabled={!selectable}
                    onClick={() => onSelect(prompt.prompt_id)}
                    className={`w-full rounded-md font-bold tabular-nums transition-colors sm:h-20 sm:text-2xl ${
                      compact ? 'h-11 text-sm' : 'h-16 text-lg'
                    } ${
                      flashing
                        ? 'animate-prompt-flash bg-amber-400 text-slate-900 motion-reduce:animate-none'
                        : prompt.is_selected
                          ? 'bg-(--color-board-tile-spent) text-slate-600'
                          : selectable
                            ? 'bg-(--color-board-tile) text-amber-300 hover:bg-amber-400 hover:text-slate-900'
                            : 'bg-(--color-board-tile) text-amber-300 opacity-90'
                    }`}
                  >
                    {prompt.is_selected && !flashing ? '—' : prompt.score_value}
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
