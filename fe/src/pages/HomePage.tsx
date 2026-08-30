import { useState } from 'react';
import { Link } from 'react-router-dom';

import SignInForm from '@/components/auth/SignInForm';
import ActiveLobbyList from '@/components/lobby/ActiveLobbyList';
import CreateLobbyModal from '@/components/lobby/CreateLobbyModal';
import MyLobbyList from '@/components/lobby/MyLobbyList';
import Card from '@/components/ui/Card';
import { useAuth } from '@/hooks/useAuth';
import { useActiveLobbies, useMyLobbies } from '@/hooks/useLobbies';

const HomePage = () => {
  const { isAuthed } = useAuth();
  const [createOpen, setCreateOpen] = useState(false);
  const activeLobbies = useActiveLobbies();
  const myLobbies = useMyLobbies();

  if (!isAuthed) {
    return (
      <div className="mx-auto max-w-sm space-y-4">
        <Card>
          <h1 className="mb-3 text-xl font-bold">Sign in</h1>
          <SignInForm />
        </Card>
        <p className="text-center text-sm text-slate-400">
          New here?{' '}
          <Link to="/register" className="font-medium text-amber-300 hover:underline">
            Create an account
          </Link>
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-6 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <ActiveLobbyList
          lobbies={activeLobbies.data ?? []}
          loading={activeLobbies.isLoading}
          error={activeLobbies.isError}
          onCreateLobby={() => setCreateOpen(true)}
        />
        <MyLobbyList
          lobbies={myLobbies.data ?? []}
          loading={myLobbies.isLoading}
          error={myLobbies.isError}
        />
      </div>
      <CreateLobbyModal open={createOpen} onClose={() => setCreateOpen(false)} />
    </div>
  );
};

export default HomePage;
