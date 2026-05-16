import { Link } from 'react-router-dom';

const NotFoundPage = () => (
  <div className="space-y-2 text-center">
    <h1 className="text-2xl font-bold">Not found</h1>
    <p className="text-slate-400">That page doesn't exist.</p>
    <Link to="/" className="text-amber-300 hover:underline">
      Go home
    </Link>
  </div>
);

export default NotFoundPage;
