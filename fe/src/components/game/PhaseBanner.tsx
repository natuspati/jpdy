import type { GameLobbyState } from '@/schemas';
import type { Role } from '@/services/game/roleFor';

interface Props {
  state: GameLobbyState;
  role: Role;
}

const personFor = (state: GameLobbyState, id: number | null): string => {
  if (id === null) return 'someone';
  if (state.host.user_id === id) return state.host.username;
  return state.players.find((p) => p.user_id === id)?.username ?? `player ${id}`;
};

function messageFor(state: GameLobbyState, role: Role): string {
  switch (state.phase) {
    case 'waiting_for_players':
      return role === 'host'
        ? 'Waiting for players. Start the game when ready.'
        : 'Waiting for the host to start the game…';
    case 'host_selecting_starting_player':
      return role === 'host' ? 'Pick a player to start.' : 'Host is choosing a starting player…';
    case 'player_selecting_prompt': {
      const who = personFor(state, state.selecting_player_id);
      return role === 'selector' ? 'Your turn — pick a prompt.' : `${who} is picking a prompt…`;
    }
    case 'player_answering': {
      const who = personFor(state, state.answering_player_id);
      return role === 'answerer'
        ? 'Your turn to answer!'
        : `${who} is answering…`;
    }
    case 'host_judging_answer':
      return role === 'host' ? 'Judge the answer.' : 'Host is judging…';
    case 'buzz_open':
      return role === 'buzzer' ? 'Buzz to answer!' : 'Buzz open…';
    case 'finished':
      return 'Game over.';
    default:
      return '';
  }
}

const PhaseBanner = ({ state, role }: Props) => (
  <div className="rounded-md border border-slate-800 bg-slate-900/70 px-3 py-2 text-sm text-slate-200">
    {messageFor(state, role)}
  </div>
);

export default PhaseBanner;
