import { useNavigate } from 'react-router-dom';

import Button from '@/components/ui/Button';
import Spinner from '@/components/ui/Spinner';
import type { ActiveLobby } from '@/schemas';

interface Props {
  lobbies: ActiveLobby[];
  loading: boolean;
  error: boolean;
}

const ActiveLobbyList = ({ lobbies, loading, error }: Props) => {
  const navigate = useNavigate();

  return (
    <section className="min-w-0 space-y-3">
      <h2 className="text-lg font-semibold text-slate-100">Active lobbies</h2>
      {loading ? (
        <Spinner />
      ) : error ? (
        <p className="text-rose-400">Active lobbies are unavailable.</p>
      ) : lobbies.length === 0 ? (
        <p className="text-slate-400">No lobbies available to join.</p>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-slate-800">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-slate-900 text-xs uppercase tracking-wide text-slate-400">
              <tr>
                <th className="px-3 py-3">Lobby ID</th>
                <th className="px-3 py-3">Host</th>
                <th className="px-3 py-3">Players</th>
                <th className="px-3 py-3">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800 bg-slate-950/40">
              {lobbies.map((lobby) => (
                <tr key={lobby.id}>
                  <td className="px-3 py-3 font-semibold text-slate-100">#{lobby.id}</td>
                  <td className="px-3 py-3 text-slate-300">{lobby.host_username}</td>
                  <td className="px-3 py-3 text-slate-300">{lobby.player_count}</td>
                  <td className="px-3 py-3">
                    <Button size="sm" onClick={() => navigate(`/lobby/${lobby.id}`)}>
                      Join
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
};

export default ActiveLobbyList;
