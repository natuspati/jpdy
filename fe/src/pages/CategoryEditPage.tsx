import { Link, useNavigate, useParams } from 'react-router-dom';

import CategoryEditor from '@/components/categories/CategoryEditor';

const CategoryEditPage = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const categoryId = id ? Number(id) : NaN;
  if (Number.isNaN(categoryId)) {
    return <p className="text-rose-400">Invalid category id.</p>;
  }
  return (
    <div className="space-y-4">
      <Link to="/categories" className="text-sm text-amber-300 hover:underline">
        ← Back to categories
      </Link>
      <CategoryEditor
        categoryId={categoryId}
        onDeleted={() => navigate('/categories', { replace: true })}
      />
    </div>
  );
};

export default CategoryEditPage;
