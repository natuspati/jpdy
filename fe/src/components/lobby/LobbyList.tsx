import Spinner from '@/components/ui/Spinner';
import { useJoinableLobbies } from '@/hooks/useLobbies';
import LobbyCard from './LobbyCard';

const LobbyList = () => {
  const { data, isLoading } = useJoinableLobbies();
  if (isLoading) return <Spinner />;
  if (!data || data.contents.length === 0) {
    return <p className="text-slate-400">No lobbies waiting to start. Create one!</p>;
  }
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
      {data.contents.map((l) => (
        <LobbyCard key={l.id} lobby={l} />
      ))}
    </div>
  );
};

export default LobbyList;
