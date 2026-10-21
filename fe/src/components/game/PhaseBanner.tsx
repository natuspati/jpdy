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
      return role === 'host' ? 'Waiting for players.' : 'Waiting for the host…';
    case 'host_selecting_starting_player':
      return role === 'host' ? 'Choose the starting player.' : 'Choosing the starting player…';
    case 'player_selecting_prompt': {
      const who = personFor(state, state.selecting_player_id);
      return role === 'selector' ? 'Your turn - pick a prompt.' : `${who} is picking a prompt…`;
    }
    case 'player_betting': {
      const who = personFor(state, state.selecting_player_id);
      return role === 'bettor'
        ? 'Bet on this clue - you picked it.'
        : `${who} is betting on the clue they picked…`;
    }
    case 'betting_open':
      return role === 'bettor'
        ? 'Outbid to answer this clue!'
        : role === 'host'
          ? 'Players are bidding.'
          : 'Players are bidding…';
    case 'player_answering': {
      const who = personFor(state, state.answering_player_id);
      return role === 'answerer'
        ? 'Answer aloud.'
        : role === 'host'
          ? `${who} is answering.`
          : `${who} is answering…`;
    }
    case 'buzz_open':
      return role === 'buzzer' ? 'Buzz to answer!' : 'Buzz open…';
    case 'answer_reveal':
      return 'Answer revealed.';
    case 'round_summary':
      return 'Round complete.';
    case 'final_betting':
      return role === 'bettor' ? 'Final: place your wager.' : 'Final: wagers are being placed…';
    case 'final_answering':
      return role === 'answerer' ? 'Final: write your answer.' : 'Final: players are answering…';
    case 'final_reveal':
      return role === 'host' ? 'Final: judge the answer.' : 'Final: revealing answers.';
    case 'finished':
      return 'Game over.';
    default:
      return '';
  }
}

const PhaseBanner = ({ state, role }: Props) => (
  <div className="rounded-md border border-slate-800 bg-slate-900/70 px-3 py-1.5 text-xs text-slate-200 sm:text-sm">
    {state.total_rounds > 1 ? (
      <p className="font-semibold text-amber-300">
        {state.categories.some(
          (category) => category.round_number === state.current_round && category.kind === 'final',
        )
          ? 'Final'
          : `Round ${state.current_round} of ${state.total_rounds}`}
      </p>
    ) : null}
    <p>{messageFor(state, role)}</p>
  </div>
);

export default PhaseBanner;
