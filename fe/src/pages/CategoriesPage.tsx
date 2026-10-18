import { useState } from 'react';
import { Link } from 'react-router-dom';

import CreateCategoryModal from '@/components/categories/CreateCategoryModal';
import Badge from '@/components/ui/Badge';
import Card from '@/components/ui/Card';
import NewItemButton from '@/components/ui/NewItemButton';
import Spinner from '@/components/ui/Spinner';
import { useMyCategories } from '@/hooks/usePromptCategories';
import { NUM_PROMPTS_IN_CATEGORY } from '@/schemas';

const CategoriesPage = () => {
  const [open, setOpen] = useState(false);
  const { data, isLoading } = useMyCategories();

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <h1 className="text-2xl font-bold">My categories</h1>
        <NewItemButton label="New category" onClick={() => setOpen(true)} />
      </div>

      {isLoading ? (
        <Spinner />
      ) : !data || data.contents.length === 0 ? (
        <p className="text-slate-400">No categories yet.</p>
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {data.contents.map((c) => {
            const promptCount = c.kind === 'final' ? 1 : NUM_PROMPTS_IN_CATEGORY;
            const promptOrders = c.prompts.map((prompt) => prompt.order);
            const complete =
              c.prompts.length === promptCount &&
              promptOrders.every((order) => order !== null && order >= 1 && order <= promptCount) &&
              new Set(promptOrders).size === promptCount;
            return (
              <Card key={c.id}>
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <Link
                      to={`/categories/${c.id}`}
                      className="text-lg font-semibold text-amber-300 hover:underline"
                    >
                      {c.name}
                    </Link>
                    <p className="text-sm text-slate-400">
                      {c.prompts.length} / {promptCount} prompts
                    </p>
                    <Badge>{c.kind === 'final' ? 'Final' : 'Standard'}</Badge>
                  </div>
                  {complete ? (
                    <Badge tone="success">Ready</Badge>
                  ) : (
                    <Badge tone="warning">Draft</Badge>
                  )}
                </div>
              </Card>
            );
          })}
        </div>
      )}

      <CreateCategoryModal open={open} onClose={() => setOpen(false)} />
    </div>
  );
};

export default CategoriesPage;
