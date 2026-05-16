import { Link, useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';

import Button from '@/components/ui/Button';
import { useAuth } from '@/hooks/useAuth';
import { useMe } from '@/hooks/useMe';

const TopBar = () => {
  const { isAuthed, signOut } = useAuth();
  const { data: me } = useMe();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const handleSignOut = () => {
    signOut();
    queryClient.clear();
    navigate('/');
  };

  return (
    <header className="sticky top-0 z-40 border-b border-slate-800 bg-slate-950/90 backdrop-blur">
      <div className="mx-auto flex w-full max-w-5xl items-center justify-between px-4 py-3 sm:px-6">
        <Link to="/" className="text-lg font-bold text-amber-400">
          Jeopardy
        </Link>
        {isAuthed ? (
          <div className="flex items-center gap-2 sm:gap-3">
            <Link
              to="/categories"
              className="text-sm font-medium text-slate-300 hover:text-amber-300"
            >
              Categories
            </Link>
            <span className="hidden text-sm text-slate-400 sm:inline">{me?.username ?? ''}</span>
            <Button variant="secondary" size="sm" onClick={handleSignOut}>
              Sign out
            </Button>
          </div>
        ) : null}
      </div>
    </header>
  );
};

export default TopBar;
