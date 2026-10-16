import type {
  BanPlayerPayload,
  GameSoundCuePayload,
  GameLobbyState,
  HostAnswerKey,
  JudgeAnswerPayload,
  SelectPromptPayload,
  SelectStarterPayload,
  SetAssetsLoadedPayload,
  StartGamePayload,
  SocketErrorPayload,
  LobbyDeletedPayload,
  UnbanPlayerPayload,
} from '@/schemas';

export interface ServerToClientEvents {
  state_changed: (state: GameLobbyState) => void;
  host_answer_key: (payload: HostAnswerKey) => void;
  game_sound_cue: (payload: GameSoundCuePayload) => void;
  lobby_deleted: (payload: LobbyDeletedPayload) => void;
  session_replaced: () => void;
  error: (payload: SocketErrorPayload) => void;
}

export interface ClientToServerEvents {
  start_game: (p?: StartGamePayload) => void;
  set_assets_loaded: (p: SetAssetsLoadedPayload) => void;
  select_starter: (p: SelectStarterPayload) => void;
  select_prompt: (p: SelectPromptPayload) => void;
  judge_answer: (p: JudgeAnswerPayload) => void;
  buzz: () => void;
  advance_answer_reveal: () => void;
  advance_round: () => void;
  ban_player: (p: BanPlayerPayload) => void;
  unban_player: (p: UnbanPlayerPayload) => void;
}

export type ClientEventName = keyof ClientToServerEvents;
