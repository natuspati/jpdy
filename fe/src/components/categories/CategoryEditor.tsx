import { useState } from 'react';

import Badge from '@/components/ui/Badge';
import Button from '@/components/ui/Button';
import Card from '@/components/ui/Card';
import ConfirmModal from '@/components/ui/ConfirmModal';
import Field from '@/components/ui/Field';
import Input from '@/components/ui/Input';
import { useCategory, useDeleteCategory, useUpdateCategory } from '@/hooks/usePromptCategories';
import { NUM_PROMPTS_IN_CATEGORY } from '@/schemas';
import PromptEditor from './PromptEditor';

interface Props {
  categoryId: number;
  onDeleted?: () => void;
}

const CategoryEditor = ({ categoryId, onDeleted }: Props) => {
  const { data, isLoading } = useCategory(categoryId);
  const update = useUpdateCategory(categoryId);
  const remove = useDeleteCategory();
  const [name, setName] = useState(data?.name ?? '');
  const [confirmingDelete, setConfirmingDelete] = useState(false);

  if (isLoading || !data) return <p className="text-slate-400">Loading…</p>;

  const isFinal = data.kind === 'final';
  const promptCount = isFinal ? 1 : NUM_PROMPTS_IN_CATEGORY;
  const slotsByOrder = new Map(
    data.prompts.filter((p) => p.order !== null).map((p) => [p.order!, p]),
  );

  const handleRename = async () => {
    if (!name || name === data.name) return;
    await update.mutateAsync({ name });
  };

  const handleDelete = async () => {
    await remove.mutateAsync(categoryId);
    setConfirmingDelete(false);
    onDeleted?.();
  };

  return (
    <div className="space-y-4 overflow-x-hidden">
      <Card>
        <div className="mb-2">
          <Badge>{isFinal ? 'Final' : 'Standard'}</Badge>
        </div>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
          <div className="flex-1">
            <Field label="Name" htmlFor="cat-name">
              <Input
                id="cat-name"
                defaultValue={data.name}
                onChange={(e) => setName(e.target.value)}
                onBlur={handleRename}
              />
            </Field>
          </div>
          <Button
            variant="danger"
            aria-label="Delete category"
            title="Delete category"
            className="w-11 shrink-0 px-0"
            onClick={() => setConfirmingDelete(true)}
          >
            X
          </Button>
        </div>
        <p className="mt-2 text-xs text-slate-400">
          {isFinal
            ? 'A Final category needs exactly one prompt, with no fixed score.'
            : `A category needs exactly ${NUM_PROMPTS_IN_CATEGORY} prompts to be usable in a lobby.`}
        </p>
      </Card>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: promptCount }).map((_, idx) => {
          const order = idx + 1;
          return (
            <PromptEditor
              key={order}
              categoryId={categoryId}
              order={order}
              kind={data.kind}
              existing={slotsByOrder.get(order)}
            />
          );
        })}
      </div>
      <ConfirmModal
        open={confirmingDelete}
        title="Delete category"
        message={`Delete category "${data.name}" and all its prompts? This cannot be undone.`}
        confirmLabel={remove.isPending ? 'Deleting…' : 'Delete category'}
        pending={remove.isPending}
        onClose={() => setConfirmingDelete(false)}
        onConfirm={() => void handleDelete()}
      />
    </div>
  );
};

export default CategoryEditor;
