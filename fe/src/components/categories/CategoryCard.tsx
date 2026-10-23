import { type FC } from 'react';
import { Link } from 'react-router-dom';

import Badge from '@/components/ui/Badge';
import { NUM_PROMPTS_IN_CATEGORY, type PromptCategoryWithPrompts } from '@/schemas';
import { formatLocalDateTime } from '@/utils/formatDateTime';

interface Props {
  category: PromptCategoryWithPrompts;
}

const CategoryCard: FC<Props> = ({ category: c }) => {
  const promptCount = c.kind === 'final' ? 1 : NUM_PROMPTS_IN_CATEGORY;
  const promptOrders = c.prompts.map((prompt) => prompt.order);
  const complete =
    c.prompts.length === promptCount &&
    promptOrders.every((order) => order !== null && order >= 1 && order <= promptCount) &&
    new Set(promptOrders).size === promptCount;

  return (
    <div
      data-complete={complete}
      className={`flex min-w-0 flex-col gap-2 rounded-lg border p-4 shadow-lg ${
        complete ? 'border-emerald-700/60 bg-emerald-950/30' : 'border-slate-800 bg-slate-900/60'
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <Link
          to={`/categories/${c.id}`}
          title={c.name}
          className="block min-w-0 truncate text-lg font-semibold text-amber-300 hover:underline"
        >
          {c.name}
        </Link>
        <div className="flex shrink-0 items-center gap-1.5">
          <Badge tone={complete ? 'success' : 'neutral'}>
            {c.prompts.length}/{promptCount}
          </Badge>
          <Badge>{c.kind === 'final' ? 'Final' : 'Standard'}</Badge>
        </div>
      </div>
      <p className="text-xs text-slate-400">Updated {formatLocalDateTime(c.updated_at)}</p>
    </div>
  );
};

export default CategoryCard;
