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
      return role === 'host'
        ? 'Choose the starting player.'
        : 'Host is choosing the starting player…';
    case 'player_selecting_prompt': {
      const who = personFor(state, state.selecting_player_id);
      return role === 'selector' ? 'Your turn — pick a prompt.' : `${who} is picking a prompt…`;
    }
    case 'player_answering': {
      const who = personFor(state, state.answering_player_id);
      return role === 'answerer'
        ? 'Answer aloud in voice chat. Host will judge.'
        : role === 'host'
          ? `Listen to ${who}'s spoken answer and judge it.`
          : `${who} is answering…`;
    }
    case 'buzz_open':
      return role === 'buzzer' ? 'Buzz to answer!' : 'Buzz open…';
    case 'answer_reveal':
      return role === 'host'
        ? 'Answer revealed. Advance to the next prompt whenever you are ready.'
        : 'Answer revealed. Waiting for the host to advance…';
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
