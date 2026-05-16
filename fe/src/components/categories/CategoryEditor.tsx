import { useState } from 'react';

import Button from '@/components/ui/Button';
import Card from '@/components/ui/Card';
import Field from '@/components/ui/Field';
import Input from '@/components/ui/Input';
import {
  useCategory,
  useDeleteCategory,
  useUpdateCategory,
} from '@/hooks/usePromptCategories';
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

  if (isLoading || !data) return <p className="text-slate-400">Loading…</p>;

  const slotsByOrder = new Map(data.prompts.filter((p) => p.order !== null).map((p) => [p.order!, p]));

  const handleRename = async () => {
    if (!name || name === data.name) return;
    await update.mutateAsync({ name });
  };

  const handleDelete = async () => {
    if (!window.confirm(`Delete category "${data.name}" and all its prompts?`)) return;
    await remove.mutateAsync(categoryId);
    onDeleted?.();
  };

  return (
    <div className="space-y-4">
      <Card>
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
          <Button variant="danger" onClick={handleDelete}>
            Delete
          </Button>
        </div>
        <p className="mt-2 text-xs text-slate-400">
          A category needs exactly {NUM_PROMPTS_IN_CATEGORY} prompts to be usable in a lobby.
        </p>
      </Card>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: NUM_PROMPTS_IN_CATEGORY }).map((_, idx) => {
          const order = idx + 1;
          return (
            <PromptEditor
              key={order}
              categoryId={categoryId}
              order={order}
              existing={slotsByOrder.get(order)}
            />
          );
        })}
      </div>
    </div>
  );
};

export default CategoryEditor;
