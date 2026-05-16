import type {
  BanPlayerPayload,
  GameLobbyState,
  JudgeAnswerPayload,
  SelectPromptPayload,
  SelectStarterPayload,
  SocketErrorPayload,
  SubmitAnswerPayload,
  UnbanPlayerPayload,
} from '@/schemas';

export interface ServerToClientEvents {
  state_changed: (state: GameLobbyState) => void;
  error: (payload: SocketErrorPayload) => void;
}

export interface ClientToServerEvents {
  start_game: () => void;
  select_starter: (p: SelectStarterPayload) => void;
  select_prompt: (p: SelectPromptPayload) => void;
  submit_answer: (p: SubmitAnswerPayload) => void;
  judge_answer: (p: JudgeAnswerPayload) => void;
  buzz: () => void;
  ban_player: (p: BanPlayerPayload) => void;
  unban_player: (p: UnbanPlayerPayload) => void;
}

export type ClientEventName = keyof ClientToServerEvents;
