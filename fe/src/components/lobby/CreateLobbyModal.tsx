import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import Badge from '@/components/ui/Badge';
import Button from '@/components/ui/Button';
import Modal from '@/components/ui/Modal';
import Spinner from '@/components/ui/Spinner';
import { useAvailableCategories } from '@/hooks/usePromptCategories';
import { useCreateLobby, useUpdateLobby } from '@/hooks/useLobbies';
import {
  MAX_CATEGORIES_PER_ROUND,
  MAX_ROUNDS_IN_LOBBY,
  MIN_ROUNDS_IN_LOBBY,
  ROUND_SCORE_MULTIPLIER,
} from '@/schemas';
import { toastError } from '@/store/toastStore';

interface Props {
  open: boolean;
  onClose: () => void;
}

const CreateLobbyModal = ({ open, onClose }: Props) => {
  const navigate = useNavigate();
  const { data, isLoading } = useAvailableCategories();
  const createLobby = useCreateLobby();
  const updateLobby = useUpdateLobby();
  // Category ids per round; the list index + 1 is the round number.
  const [rounds, setRounds] = useState<number[][]>([[]]);

  useEffect(() => {
    if (!open) setRounds([[]]);
  }, [open]);

  const toggle = (roundIndex: number, id: number) => {
    setRounds((prev) =>
      prev.map((ids, index) => {
        if (index !== roundIndex) return ids;
        if (ids.includes(id)) return ids.filter((existing) => existing !== id);
        return ids.length < MAX_CATEGORIES_PER_ROUND ? [...ids, id] : ids;
      }),
    );
  };

  const addRound = () => setRounds((prev) => [...prev, []]);
  const removeRound = (roundIndex: number) =>
    setRounds((prev) => prev.filter((_, index) => index !== roundIndex));

  const everyRoundHasCategory = rounds.every((ids) => ids.length > 0);

  const handleStart = async () => {
    if (!everyRoundHasCategory) {
      toastError('Pick at least one category in every round');
      return;
    }
    const lobby = await createLobby.mutateAsync();
    await updateLobby.mutateAsync({
      id: lobby.id,
      payload: { rounds },
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

  return (
    <Modal open={open} onClose={onClose} title="New lobby">
      <div className="space-y-3">
        <p className="text-sm text-slate-400">
          Pick the categories for each round. A category can be used once, and prompt values double
          every round. Only categories with all prompts filled are shown.
        </p>
        {isLoading ? (
          <Spinner />
        ) : categories.length === 0 ? (
          <p className="text-sm text-slate-400">
            No ready categories yet. Create one in the Categories page first.
          </p>
        ) : (
          <div className="max-h-96 space-y-4 overflow-y-auto">
            {rounds.map((ids, roundIndex) => (
              <fieldset key={roundIndex} className="space-y-2">
                <legend className="flex w-full items-center justify-between gap-2 text-sm font-semibold text-slate-100">
                  <span>
                    Round {roundIndex + 1}{' '}
                    <span className="font-normal text-slate-400">
                      (values ×{ROUND_SCORE_MULTIPLIER ** roundIndex}, {ids.length}/
                      {MAX_CATEGORIES_PER_ROUND} categories)
                    </span>
                  </span>
                  {rounds.length > MIN_ROUNDS_IN_LOBBY ? (
                    <Button
                      type="button"
                      size="compact"
                      variant="ghost"
                      aria-label={`Remove round ${roundIndex + 1}`}
                      onClick={() => removeRound(roundIndex)}
                    >
                      Remove round
                    </Button>
                  ) : null}
                </legend>
                <ul className="space-y-2">
                  {categories.map((c) => {
                    const checked = ids.includes(c.id);
                    const usedElsewhere = !checked && rounds.some((other) => other.includes(c.id));
                    const roundFull = !checked && ids.length >= MAX_CATEGORIES_PER_ROUND;
                    return (
                      <li key={c.id}>
                        <label
                          className={`flex items-center justify-between gap-2 rounded-md border border-slate-800 bg-slate-900/40 p-2 ${
                            usedElsewhere || roundFull
                              ? 'cursor-not-allowed opacity-50'
                              : 'cursor-pointer hover:bg-slate-900'
                          }`}
                        >
                          <span className="flex items-center gap-2">
                            <input
                              type="checkbox"
                              className="h-4 w-4 accent-amber-400"
                              aria-label={`${c.name} in round ${roundIndex + 1}`}
                              checked={checked}
                              disabled={usedElsewhere || roundFull}
                              onChange={() => toggle(roundIndex, c.id)}
                            />
                            <span className="text-sm text-slate-100">{c.name}</span>
                          </span>
                          <Badge>{c.prompts.length} prompts</Badge>
                        </label>
                      </li>
                    );
                  })}
                </ul>
              </fieldset>
            ))}
          </div>
        )}
        <div className="flex flex-wrap items-center justify-between gap-2">
          <Button
            type="button"
            variant="secondary"
            disabled={rounds.length >= MAX_ROUNDS_IN_LOBBY}
            onClick={addRound}
          >
            Add round
          </Button>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="ghost" onClick={onClose}>
              Cancel
            </Button>
            <Button type="button" disabled={busy || !everyRoundHasCategory} onClick={handleStart}>
              {busy ? 'Creating…' : 'Create & open'}
            </Button>
          </div>
        </div>
      </div>
    </Modal>
  );
};

export default CreateLobbyModal;
