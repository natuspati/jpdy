import { useState } from 'react';
import { Link } from 'react-router-dom';

import CreateCategoryModal from '@/components/categories/CreateCategoryModal';
import Badge from '@/components/ui/Badge';
import Button from '@/components/ui/Button';
import Card from '@/components/ui/Card';
import Spinner from '@/components/ui/Spinner';
import { useMyCategories } from '@/hooks/usePromptCategories';
import { NUM_PROMPTS_IN_CATEGORY } from '@/schemas';

const CategoriesPage = () => {
  const [open, setOpen] = useState(false);
  const { data, isLoading } = useMyCategories();

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">My categories</h1>
        <Button onClick={() => setOpen(true)}>New category</Button>
      </div>

      {isLoading ? (
        <Spinner />
      ) : !data || data.contents.length === 0 ? (
        <p className="text-slate-400">No categories yet.</p>
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {data.contents.map((c) => {
            const complete = c.prompts.length === NUM_PROMPTS_IN_CATEGORY;
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
                      {c.prompts.length} / {NUM_PROMPTS_IN_CATEGORY} prompts
                    </p>
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
