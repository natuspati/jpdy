import { useMemo } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

import AnswerInput from '@/components/game/AnswerInput';
import BuzzButton from '@/components/game/BuzzButton';
import FinalLeaderboard from '@/components/game/FinalLeaderboard';
import GameBoard from '@/components/game/GameBoard';
import HostControls from '@/components/game/HostControls';
import HostJudgePanel from '@/components/game/HostJudgePanel';
import PhaseBanner from '@/components/game/PhaseBanner';
import PromptStage from '@/components/game/PromptStage';
import ScoreBoard from '@/components/game/ScoreBoard';
import TimerBar from '@/components/game/TimerBar';
import Button from '@/components/ui/Button';
import Card from '@/components/ui/Card';
import Spinner from '@/components/ui/Spinner';
import { useAuth } from '@/hooks/useAuth';
import { useLobbySocket } from '@/hooks/useLobbySocket';
import { currentPrompt } from '@/services/game/gameDerivations';
import { canBuzz, canSubmitAnswer } from '@/services/game/phaseGuards';
import { roleFor } from '@/services/game/roleFor';

const LobbyPage = () => {
  const { id } = useParams<{ id: string }>();
  const lobbyId = id ? Number(id) : undefined;
  const lobbyIdSafe = lobbyId !== undefined && !Number.isNaN(lobbyId) ? lobbyId : undefined;
  const navigate = useNavigate();
  const { token, userId } = useAuth();
  const { state, hostJudgingAnswer, status, emit, reason } = useLobbySocket({
    lobbyId: lobbyIdSafe,
    token,
  });

  const view = useMemo(() => {
    if (!state || userId === null) return null;
    return {
      role: roleFor(state, userId),
      currentPrompt: currentPrompt(state),
    };
  }, [state, userId]);

  if (lobbyIdSafe === undefined) {
    return <p className="text-rose-400">Invalid lobby id.</p>;
  }
  if (userId === null) {
    return <p className="text-rose-400">Not signed in.</p>;
  }
  if (status === 'failed') {
    return (
      <Card className="space-y-3 text-center">
        <p className="text-rose-300">Could not connect to lobby.</p>
        {reason ? <p className="text-sm text-slate-400">{reason}</p> : null}
        <Button onClick={() => navigate('/')}>Back to lobbies</Button>
      </Card>
    );
  }
  if (status === 'closed') {
    return (
      <Card className="space-y-3 text-center">
        <p className="text-rose-300">Lobby connection closed.</p>
        <p className="text-sm text-slate-400">
          {reason ?? 'You may have been removed from the lobby or the game ended.'}
        </p>
        <Button onClick={() => navigate('/')}>Back to lobbies</Button>
      </Card>
    );
  }
  if (!state || !view) {
    return (
      <div className="flex items-center gap-2 text-slate-400">
        <Spinner />
        Connecting…
      </div>
    );
  }

  const totalSecondsForPhase = state.phase === 'buzz_open' ? 10 : 30;
  const isFinished = state.phase === 'finished';
  const showPromptStage =
    !!view.currentPrompt &&
    ['player_answering', 'host_judging_answer', 'buzz_open'].includes(state.phase);
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-[2fr_1fr]">
      <div className="space-y-3">
        <PhaseBanner state={state} role={view.role} />
        {isFinished ? (
          <FinalLeaderboard state={state} />
        ) : (
          <GameBoard
            state={state}
            currentUserId={userId}
            onSelect={(promptId) => emit('select_prompt', { prompt_id: promptId })}
          />
        )}
        {showPromptStage && view.currentPrompt ? (
          <PromptStage
            prompt={view.currentPrompt}
          />
        ) : null}
      </div>

      <aside className="space-y-3">
        <ScoreBoard
          state={state}
          currentUserId={userId}
          onBan={(uid) => emit('ban_player', { user_id: uid })}
          onUnban={(uid) => emit('unban_player', { user_id: uid })}
        />
        <TimerBar deadline={state.timer_deadline} totalSeconds={totalSecondsForPhase} />

        {view.role === 'host' ? (
          <HostControls
            state={state}
            currentUserId={userId}
            onStart={() => emit('start_game')}
            onSelectStarter={(uid) => emit('select_starter', { user_id: uid })}
          />
        ) : null}

        {view.role === 'host' && state.phase === 'host_judging_answer' ? (
          <HostJudgePanel
            submittedAnswer={hostJudgingAnswer?.submitted_answer ?? state.last_submitted_answer}
            expectedAnswer={hostJudgingAnswer?.expected_answer}
            onJudge={(correct) => emit('judge_answer', { correct })}
          />
        ) : null}

        {canSubmitAnswer(state, userId) ? (
          <AnswerInput onSubmit={(text) => emit('submit_answer', { text })} />
        ) : null}

        {state.phase === 'buzz_open' && view.role !== 'host' ? (
          <BuzzButton enabled={canBuzz(state, userId)} onBuzz={() => emit('buzz')} />
        ) : null}
      </aside>
    </div>
  );
};

export default LobbyPage;
