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
  // A single row of columns fills the height left by the page, and tiles shrink to fit, so the
  // board never needs its own scrollbar. Wrapped 6+ layouts (below md) keep fixed tile heights.
  const compact = categories.length <= 5;
  return (
    <div
      className={`grid min-h-0 flex-1 ${compact ? 'grid-rows-1 gap-1 sm:gap-2' : 'gap-2 md:grid-rows-1'} ${colsClass}`}
    >
      {categories.map((cat) => (
        <div key={cat.category_id} className="flex min-h-0 flex-col gap-1 sm:gap-2">
          <div
            className={`flex shrink-0 min-w-0 items-center justify-center overflow-hidden rounded-md bg-(--color-board-bg) text-center font-semibold uppercase tracking-wide text-amber-300 ${
              compact ? 'h-12 p-1 text-[10px] sm:h-14 sm:p-2 sm:text-sm' : 'h-[4.5rem] p-2 text-sm'
            }`}
          >
            <span className="line-clamp-2 min-w-0 break-words">{cat.name}</span>
          </div>
          <div
            className={`flex flex-col gap-1 sm:gap-2 ${compact ? 'min-h-0 flex-1' : 'md:min-h-0 md:flex-1'}`}
          >
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
                    className={`w-full rounded-md font-bold tabular-nums transition-colors ${
                      compact
                        ? 'min-h-8 max-h-16 flex-1 basis-0 text-sm sm:max-h-20 sm:text-2xl'
                        : 'h-16 text-lg md:h-auto md:min-h-8 md:max-h-20 md:flex-1 md:basis-0 md:text-2xl'
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
