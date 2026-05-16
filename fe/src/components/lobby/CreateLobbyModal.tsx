import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import Badge from '@/components/ui/Badge';
import Button from '@/components/ui/Button';
import Modal from '@/components/ui/Modal';
import Spinner from '@/components/ui/Spinner';
import { useAvailableCategories } from '@/hooks/usePromptCategories';
import { useCreateLobby, useUpdateLobby } from '@/hooks/useLobbies';
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
  const [selected, setSelected] = useState<Set<number>>(new Set());

  useEffect(() => {
    if (!open) setSelected(new Set());
  }, [open]);

  const toggle = (id: number) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleStart = async () => {
    if (selected.size === 0) {
      toastError('Pick at least one category');
      return;
    }
    const lobby = await createLobby.mutateAsync();
    await updateLobby.mutateAsync({
      id: lobby.id,
      payload: { prompt_category_ids: Array.from(selected) },
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
          Pick the categories you want to play. Only categories with all prompts filled are
          shown.
        </p>
        {isLoading ? (
          <Spinner />
        ) : categories.length === 0 ? (
          <p className="text-sm text-slate-400">
            No ready categories yet. Create one in the Categories page first.
          </p>
        ) : (
          <ul className="max-h-72 space-y-2 overflow-y-auto">
            {categories.map((c) => (
              <li key={c.id}>
                <label className="flex cursor-pointer items-center justify-between gap-2 rounded-md border border-slate-800 bg-slate-900/40 p-2 hover:bg-slate-900">
                  <span className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      className="h-4 w-4 accent-amber-400"
                      checked={selected.has(c.id)}
                      onChange={() => toggle(c.id)}
                    />
                    <span className="text-sm text-slate-100">{c.name}</span>
                  </span>
                  <Badge>{c.prompts.length} prompts</Badge>
                </label>
              </li>
            ))}
          </ul>
        )}
        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="button" disabled={busy || selected.size === 0} onClick={handleStart}>
            {busy ? 'Creating…' : 'Create & open'}
          </Button>
        </div>
      </div>
    </Modal>
  );
};

export default CreateLobbyModal;
