import type { GameLobbyState, GamePromptState } from '@/schemas';
import MediaRenderer from './MediaRenderer';
import { findPromptById } from '@/services/game/gameDerivations';

interface Props {
  state: GameLobbyState;
  prompt: GamePromptState;
  showAnswer: boolean;
}

const PromptStage = ({ state, prompt, showAnswer }: Props) => {
  // Re-find by id so the answer/question types stay in sync if backend ever splits them.
  const live = findPromptById(state, prompt.prompt_id) ?? prompt;
  return (
    <div className="flex flex-col items-center gap-4 rounded-md border border-slate-800 bg-slate-900/70 p-4">
      <div className="text-xs uppercase tracking-wide text-amber-300">
        {live.score_value} pts
      </div>
      <MediaRenderer type={getQuestionType(state, live)} value={live.question} />
      {showAnswer ? (
        <div className="w-full border-t border-slate-800 pt-3">
          <p className="text-center text-xs uppercase tracking-wide text-slate-400">Answer</p>
          <MediaRenderer type={getAnswerType(state, live)} value={live.answer} />
        </div>
      ) : null}
    </div>
  );
};

// The game state snapshot stores question/answer text only — types live in the
// original prompt model. We look them up from the lobby's category list (which
// the BE materializes to the same shape) by walking categories; if missing,
// default to 'text'.
function getQuestionType(_state: GameLobbyState, _prompt: GamePromptState) {
  // GamePromptState in the materialized state currently only stores text;
  // BE plan is to include media types in the materialization. Default to text.
  return 'text' as const;
}
function getAnswerType(_state: GameLobbyState, _prompt: GamePromptState) {
  return 'text' as const;
}

export default PromptStage;
