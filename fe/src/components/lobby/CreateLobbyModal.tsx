import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import Badge from '@/components/ui/Badge';
import Button from '@/components/ui/Button';
import Field from '@/components/ui/Field';
import Input from '@/components/ui/Input';
import Modal from '@/components/ui/Modal';
import Spinner from '@/components/ui/Spinner';
import { useAuth } from '@/hooks/useAuth';
import { useDebouncedValue } from '@/hooks/useDebouncedValue';
import { useAvailableCategories } from '@/hooks/usePromptCategories';
import { useCreateLobby, useUpdateLobby } from '@/hooks/useLobbies';
import {
  BETTING_PROMPT_DEFAULT_PERCENT,
  MAX_BETTING_PROMPTS_PER_ROUND,
  MAX_CATEGORIES_PER_ROUND,
  MAX_ROUNDS_IN_LOBBY,
  MIN_ROUNDS_IN_LOBBY,
  ROUND_SCORE_MULTIPLIER,
  type PromptCategoryWithPrompts,
} from '@/schemas';
import { toastError } from '@/store/toastStore';
import { formatLocalDateTime } from '@/utils/formatDateTime';

interface Props {
  open: boolean;
  onClose: () => void;
}

type Category = PromptCategoryWithPrompts;

const SEARCH_DEBOUNCE_MS = 300;

const CreateLobbyModal = ({ open, onClose }: Props) => {
  const navigate = useNavigate();
  const { userId } = useAuth();
  const [search, setSearch] = useState('');
  const debouncedSearch = useDebouncedValue(search.trim(), SEARCH_DEBOUNCE_MS);
  const { data, isLoading } = useAvailableCategories('standard', debouncedSearch);
  const { data: finalData, isLoading: finalLoading } = useAvailableCategories('final');
  const createLobby = useCreateLobby();
  const updateLobby = useUpdateLobby();
  // Picked categories per round (kept whole, so they survive new searches); the list index + 1
  // is the round number.
  const [rounds, setRounds] = useState<Category[][]>([[]]);
  const [activeRound, setActiveRound] = useState(0);
  // Blank means the server default (10% of a round's prompts, rounded down).
  const [bettingCount, setBettingCount] = useState('');
  const [finalCategoryId, setFinalCategoryId] = useState<number | null>(null);

  useEffect(() => {
    if (!open) {
      setSearch('');
      setRounds([[]]);
      setActiveRound(0);
      setBettingCount('');
      setFinalCategoryId(null);
    }
  }, [open]);

  const usedIds = new Set(rounds.flat().map((category) => category.id));
  const activeFull = rounds[activeRound].length >= MAX_CATEGORIES_PER_ROUND;

  const addToActiveRound = (category: Category) => {
    if (activeFull || usedIds.has(category.id)) return;
    setRounds((prev) =>
      prev.map((picked, index) => (index === activeRound ? [...picked, category] : picked)),
    );
  };

  const removeFromRound = (roundIndex: number, id: number) => {
    setRounds((prev) =>
      prev.map((picked, index) =>
        index === roundIndex ? picked.filter((category) => category.id !== id) : picked,
      ),
    );
  };

  const addRound = () => {
    setRounds((prev) => [...prev, []]);
    setActiveRound(rounds.length);
  };
  const removeRound = (roundIndex: number) => {
    setRounds((prev) => prev.filter((_, index) => index !== roundIndex));
    setActiveRound(
      Math.min(activeRound > roundIndex ? activeRound - 1 : activeRound, rounds.length - 2),
    );
  };

  const everyRoundHasCategory = rounds.every((picked) => picked.length > 0);
  const bettingValue = Number(bettingCount);
  const bettingInvalid =
    bettingCount !== '' &&
    (!Number.isInteger(bettingValue) ||
      bettingValue < 0 ||
      bettingValue > MAX_BETTING_PROMPTS_PER_ROUND);

  const handleStart = async () => {
    if (bettingInvalid) {
      toastError(`Betting prompts must be 0 to ${MAX_BETTING_PROMPTS_PER_ROUND}`);
      return;
    }
    if (!everyRoundHasCategory) {
      toastError('Pick at least one category in every round');
      return;
    }
    const lobby = await createLobby.mutateAsync();
    await updateLobby.mutateAsync({
      id: lobby.id,
      payload: {
        rounds: rounds.map((picked) => picked.map((category) => category.id)),
        final_category_id: finalCategoryId,
        ...(bettingCount === '' ? {} : { betting_prompt_count: bettingValue }),
      },
    });
    await updateLobby.mutateAsync({
      id: lobby.id,
      payload: { state: 'waiting_start' },
    });
    onClose();
    // Host auto-joins immediately after promoting the lobby.
    navigate(`/lobby/${lobby.id}`);
  };

  const busy = createLobby.isPending || updateLobby.isPending;
  const categories = data?.contents ?? [];

  // Mirrors the server: an explicit count is clamped to the round's size, else a percent of it.
  const bettingPreview = bettingInvalid
    ? []
    : rounds.map((picked, index) => {
        const promptCount = picked.reduce((sum, c) => sum + c.prompts.length, 0);
        const count =
          bettingCount === ''
            ? Math.floor((promptCount * BETTING_PROMPT_DEFAULT_PERCENT) / 100)
            : Math.min(bettingValue, promptCount);
        return { round: index + 1, promptCount, count };
      });

  return (
    <Modal open={open} onClose={onClose} title="New lobby" size="wide">
      <div className="space-y-3">
        <p className="text-sm text-slate-400">
          Search for categories and click one to add it to the selected round. A category can be
          used once, and prompt values double every round. Only categories with all prompts filled
          are shown.
        </p>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <section aria-label="Rounds" className="min-w-0 space-y-3 md:col-start-2 md:row-start-1">
            <div className="flex flex-wrap gap-2">
              {rounds.map((picked, roundIndex) => (
                <Button
                  key={roundIndex}
                  type="button"
                  size="compact"
                  variant={roundIndex === activeRound ? 'primary' : 'secondary'}
                  aria-pressed={roundIndex === activeRound}
                  onClick={() => setActiveRound(roundIndex)}
                >
                  Round {roundIndex + 1}
                  <span aria-hidden="true" className="ml-1 font-normal">
                    ({picked.length})
                  </span>
                </Button>
              ))}
              <Button
                type="button"
                size="compact"
                variant="ghost"
                disabled={rounds.length >= MAX_ROUNDS_IN_LOBBY}
                onClick={addRound}
              >
                Add round
              </Button>
            </div>
            <div className="flex items-center justify-between gap-2 text-sm">
              <span className="text-slate-400">
                Round {activeRound + 1}: values ×{ROUND_SCORE_MULTIPLIER ** activeRound},{' '}
                {rounds[activeRound].length}/{MAX_CATEGORIES_PER_ROUND} categories
              </span>
              {rounds.length > MIN_ROUNDS_IN_LOBBY ? (
                <Button
                  type="button"
                  size="compact"
                  variant="ghost"
                  aria-label={`Remove round ${activeRound + 1}`}
                  onClick={() => removeRound(activeRound)}
                >
                  Remove round
                </Button>
              ) : null}
            </div>
            {rounds[activeRound].length === 0 ? (
              <p className="text-sm text-slate-500">No categories in this round yet.</p>
            ) : (
              <ul className="flex flex-wrap gap-2">
                {rounds[activeRound].map((category) => (
                  <li
                    key={category.id}
                    className="flex min-w-0 items-center gap-1 rounded-full bg-slate-800 py-1 pl-3 pr-1 text-sm text-slate-100"
                  >
                    <span className="max-w-40 truncate">{category.name}</span>
                    <button
                      type="button"
                      aria-label={`Remove ${category.name} from round ${activeRound + 1}`}
                      className="h-5 w-5 rounded-full leading-none hover:bg-slate-700"
                      onClick={() => removeFromRound(activeRound, category.id)}
                    >
                      ×
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>
          <section
            aria-label="Categories"
            className="min-w-0 space-y-2 md:col-start-1 md:row-start-1"
          >
            <Input
              type="search"
              aria-label="Search categories"
              placeholder="Search categories"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
            {isLoading ? (
              <Spinner />
            ) : categories.length === 0 ? (
              <p className="text-sm text-slate-400">
                {debouncedSearch
                  ? 'No ready categories match your search.'
                  : 'No ready categories yet. Create one in the Categories page first.'}
              </p>
            ) : (
              <ul className="max-h-72 space-y-2 overflow-y-auto">
                {categories.map((c) => {
                  const used = usedIds.has(c.id);
                  return (
                    <li key={c.id}>
                      <button
                        type="button"
                        aria-label={`Add ${c.name} to round ${activeRound + 1}`}
                        disabled={used || activeFull}
                        onClick={() => addToActiveRound(c)}
                        className="flex w-full min-w-0 items-center justify-between gap-2 rounded-md border border-slate-800 bg-slate-900/40 p-2 text-left hover:bg-slate-900 disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:bg-slate-900/40"
                      >
                        <span className="min-w-0">
                          <span className="flex items-center gap-2">
                            <span className="truncate text-sm text-slate-100">{c.name}</span>
                            {userId !== null && c.owner_id === userId ? (
                              <Badge tone="info">Yours</Badge>
                            ) : null}
                          </span>
                          <span className="block text-xs text-slate-400">
                            Updated {formatLocalDateTime(c.updated_at)}
                          </span>
                        </span>
                        <span className="flex shrink-0 items-center gap-2">
                          {used ? <Badge tone="success">Added</Badge> : null}
                          <Badge>{c.prompts.length} prompts</Badge>
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </section>
        </div>
        <Field
          label="Final category (optional)"
          htmlFor="final-category"
          hint="One scoreless prompt after all normal rounds. Only ready Final categories are shown."
        >
          <select
            id="final-category"
            className="h-11 w-full rounded-md border border-slate-700 bg-slate-950 px-3 text-slate-100"
            value={finalCategoryId ?? ''}
            disabled={busy || finalLoading}
            onChange={(event) =>
              setFinalCategoryId(event.target.value === '' ? null : Number(event.target.value))
            }
          >
            <option value="">No final</option>
            {finalData?.contents.map((category) => (
              <option key={category.id} value={category.id}>
                {category.name}
              </option>
            ))}
          </select>
        </Field>
        <Field
          label="Betting prompts in each round"
          htmlFor="betting-prompt-count"
          hint={`A number of prompts, not a percent. 0 = none. Blank = automatic: ${BETTING_PROMPT_DEFAULT_PERCENT}% of a round's prompts, rounded down.`}
          error={
            bettingInvalid
              ? `Enter a whole number from 0 to ${MAX_BETTING_PROMPTS_PER_ROUND}.`
              : undefined
          }
        >
          <Input
            id="betting-prompt-count"
            type="number"
            min={0}
            max={MAX_BETTING_PROMPTS_PER_ROUND}
            step={1}
            placeholder="Auto"
            value={bettingCount}
            invalid={bettingInvalid}
            onChange={(event) => setBettingCount(event.target.value)}
          />
        </Field>
        {bettingPreview.some((r) => r.promptCount > 0) ? (
          <ul aria-label="Betting prompts preview" className="space-y-0.5 text-xs text-slate-400">
            {bettingPreview
              .filter((r) => r.promptCount > 0)
              .map((r) => (
                <li key={r.round}>
                  Round {r.round}: {r.count} of {r.promptCount} prompts will be betting prompts
                </li>
              ))}
          </ul>
        ) : null}
        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button
            type="button"
            disabled={busy || !everyRoundHasCategory || bettingInvalid}
            onClick={handleStart}
          >
            {busy ? 'Creating…' : 'Create & open'}
          </Button>
        </div>
      </div>
    </Modal>
  );
};

export default CreateLobbyModal;
