import { useEffect, useMemo } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

import BuzzButton from '@/components/game/BuzzButton';
import FinalLeaderboard from '@/components/game/FinalLeaderboard';
import GameBoard from '@/components/game/GameBoard';
import HostControls from '@/components/game/HostControls';
import HostJudgePanel from '@/components/game/HostJudgePanel';
import PhaseBanner from '@/components/game/PhaseBanner';
import PromptStage from '@/components/game/PromptStage';
import ScoreBoard from '@/components/game/ScoreBoard';
import TimerBar from '@/components/game/TimerBar';
import GameSoundControls from '@/components/game/GameSoundControls';
import { useGameAudio } from '@/audio/useGameAudio';
import Button from '@/components/ui/Button';
import Card from '@/components/ui/Card';
import Spinner from '@/components/ui/Spinner';
import { useAuth } from '@/hooks/useAuth';
import { useLobbySocket } from '@/hooks/useLobbySocket';
import { currentPrompt } from '@/services/game/gameDerivations';
import { canBuzz } from '@/services/game/phaseGuards';
import { roleFor } from '@/services/game/roleFor';
import { timerSecondsForPhase } from '@/services/game/gameTiming';
import { toastSuccess } from '@/store/toastStore';

const LobbyPage = () => {
  const { id } = useParams<{ id: string }>();
  const lobbyId = id ? Number(id) : undefined;
  const lobbyIdSafe = lobbyId !== undefined && !Number.isNaN(lobbyId) ? lobbyId : undefined;
  const navigate = useNavigate();
  const { token, userId } = useAuth();
  const { syncGameState, playCue, stopAll } = useGameAudio();
  const { state, hostAnswerKey, soundCue, lobbyDeleted, status, emit, reconnect, reason } =
    useLobbySocket({
      lobbyId: lobbyIdSafe,
      token,
    });

  useEffect(() => {
    syncGameState(state);
  }, [state, syncGameState]);

  useEffect(() => {
    if (soundCue) playCue(soundCue);
  }, [playCue, soundCue]);

  useEffect(() => {
    if (!lobbyDeleted) return;
    stopAll();
    toastSuccess('Lobby deleted by host');
    navigate('/', { replace: true });
  }, [lobbyDeleted, navigate, stopAll]);

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
        <div className="flex justify-center gap-2">
          <Button onClick={reconnect}>Reconnect</Button>
          <Button variant="secondary" onClick={() => navigate('/')}>
            Back to lobbies
          </Button>
        </div>
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
        <div className="flex justify-center gap-2">
          <Button onClick={reconnect}>Reconnect</Button>
          <Button variant="secondary" onClick={() => navigate('/')}>
            Back to lobbies
          </Button>
        </div>
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

  const totalSecondsForPhase = timerSecondsForPhase(state.phase);
  const isFinished = state.phase === 'finished';
  const showBoard = [
    'waiting_for_players',
    'host_selecting_starting_player',
    'player_selecting_prompt',
  ].includes(state.phase);
  const showPromptStage =
    !!view.currentPrompt &&
    ['player_answering', 'buzz_open', 'answer_reveal'].includes(state.phase);
  const answerer = state.answering_player_id
    ? state.players.find((player) => player.user_id === state.answering_player_id)
    : undefined;
  const buzzDisabledReason = (() => {
    if (canBuzz(state, userId)) return undefined;
    const player = state.players.find((item) => item.user_id === userId);
    if (!player || player.is_banned) return 'Banned players cannot buzz.';
    if (player.connection_status !== 'connected') return 'Reconnect to buzz.';
    if (state.attempted_player_ids.includes(userId)) return 'You already attempted this clue.';
    return 'You cannot buzz right now.';
  })();
  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-[3fr_2fr]">
      <div className="space-y-3">
        {isFinished ? (
          <FinalLeaderboard state={state} />
        ) : showBoard ? (
          <GameBoard
            state={state}
            currentUserId={userId}
            onSelect={(promptId) => emit('select_prompt', { prompt_id: promptId })}
          />
        ) : null}
        {showPromptStage && view.currentPrompt ? (
          <PromptStage
            prompt={view.currentPrompt}
            answer={state.phase === 'answer_reveal' ? state.resolved_answer : null}
            answerType={state.phase === 'answer_reveal' ? state.resolved_answer_type : null}
            answerMedia={state.phase === 'answer_reveal' ? state.resolved_answer_media : null}
            resolution={state.phase === 'answer_reveal' ? state.resolution : null}
          />
        ) : null}
      </div>

      <aside className="flex flex-col gap-3 lg:sticky lg:top-4 lg:self-start">
        {status === 'connecting' ? (
          <p className="rounded border border-amber-500/50 bg-amber-950/40 px-3 py-2 text-sm text-amber-200">
            {reason ?? 'Connecting…'}
          </p>
        ) : null}
        <div className="order-2 lg:order-1">
          <ScoreBoard
            state={state}
            currentUserId={userId}
            onBan={(uid) => emit('ban_player', { user_id: uid })}
            onUnban={(uid) => emit('unban_player', { user_id: uid })}
          />
        </div>
        <div className="order-3 space-y-3 lg:order-2">
          <PhaseBanner state={state} role={view.role} />
          <TimerBar deadline={state.timer_deadline} totalSeconds={totalSecondsForPhase} />
          <GameSoundControls />
        </div>
        <div className="order-1 lg:order-3">
          {view.role === 'host' ? (
            <HostControls
              state={state}
              currentUserId={userId}
              onStart={() => emit('start_game')}
              onSelectStarter={(uid) => emit('select_starter', { user_id: uid })}
              onAdvanceAnswerReveal={() => emit('advance_answer_reveal')}
            />
          ) : null}

          {view.role === 'host' && state.phase === 'player_answering' && answerer ? (
            <HostJudgePanel
              answeringPlayerName={answerer.username}
              expectedAnswer={hostAnswerKey?.expected_answer}
              onJudge={(correct) => emit('judge_answer', { correct })}
            />
          ) : null}

          {state.phase === 'buzz_open' && view.role !== 'host' ? (
            <BuzzButton
              enabled={canBuzz(state, userId)}
              disabledReason={buzzDisabledReason}
              onBuzz={() => emit('buzz')}
            />
          ) : null}
        </div>
      </aside>
    </div>
  );
};

export default LobbyPage;
