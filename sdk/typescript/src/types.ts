/**
 * Type definitions for the Werewolf Arena SDK.
 */

export enum GamePhase {
  WAITING = 'waiting',
  ROLE_ASSIGNMENT = 'role_assignment',
  NIGHT_START = 'night_start',
  NIGHT_WEREWOLF = 'night_werewolf',
  NIGHT_SEER = 'night_seer',
  NIGHT_WITCH = 'night_witch',
  NIGHT_HUNTER = 'night_hunter',
  NIGHT_GUARD = 'night_guard',
  NIGHT_END = 'night_end',
  DAY_ANNOUNCEMENT = 'day_announcement',
  DAY_SPEECH = 'day_speech',
  DAY_VOTE = 'day_vote',
  DAY_VOTE_RESULT = 'day_vote_result',
  HUNTER_SHOOT = 'hunter_shoot',
  LAST_WORDS = 'last_words',
  GAME_OVER = 'game_over',
}

export enum Faction {
  WEREWOLF = 'werewolf',
  VILLAGER = 'villager',
  GOD = 'god',
}

export enum ActionType {
  WEREWOLF_KILL = 'werewolf_kill',
  WEREWOLF_CHAT = 'werewolf_chat',
  SEER_CHECK = 'seer_check',
  WITCH_SAVE = 'witch_save',
  WITCH_POISON = 'witch_poison',
  WITCH_SKIP = 'witch_skip',
  GUARD_PROTECT = 'guard_protect',
  HUNTER_SHOOT = 'hunter_shoot',
  HUNTER_SKIP = 'hunter_skip',
  SPEECH = 'speech',
  VOTE = 'vote',
  VOTE_ABSTAIN = 'vote_abstain',
  LAST_WORDS = 'last_words',
}

export enum RoomStatus {
  WAITING = 'waiting',
  READY = 'ready',
  PLAYING = 'playing',
  FINISHED = 'finished',
  CANCELLED = 'cancelled',
}

export interface PlayerInfo {
  seat: number;
  agentName?: string;
  isAlive: boolean;
  role?: string;
}

export interface PhaseInfo {
  phase: GamePhase;
  round: number;
  timeoutSeconds?: number;
}

export interface RoleConfig {
  werewolf?: number;
  seer?: number;
  witch?: number;
  hunter?: number;
  guard?: number;
  idiot?: number;
  villager?: number;
  [key: string]: number | undefined;
}

export interface GameState {
  gameId: string;
  roomId?: string;
  status: string;
  currentPhase?: string;
  currentRound: number;
  mySeat?: number;
  myRole?: string;
  players: PlayerInfo[];
  startedAt?: string;
  finishedAt?: string;
  winner?: string;
}

export interface GameEvent {
  eventType: string;
  gameId: string;
  timestamp?: string;
  round?: number;
  phase?: string;
  data: Record<string, any>;
  visibility?: string;
}

export interface Action {
  actionType: string;
  target?: number;
  content?: string;
  metadata?: Record<string, any>;
}

export interface ActionRequestBody {
  action_type: string;
  target_seat?: number;
  content?: string;
  metadata?: Record<string, any>;
}

export interface ActionResponse {
  success: boolean;
  action_id?: string;
  message: string;
}

export interface RoomInfo {
  id: string;
  name: string;
  status: string;
  playerCount: number;
  currentPlayers: number;
  config: Record<string, any>;
  createdAt?: string;
}

export interface SlotInfo {
  seat: number;
  agentId?: string;
  agentName?: string;
  status: string;
}

export interface JoinResponse {
  seat: number;
  room_id: string;
  agent_id: string;
  message: string;
}

export interface SpeechRecord {
  seat: number;
  content: string;
  agentName?: string;
  timestamp?: string;
}

export interface AvailableAction {
  action_type: string;
  description: string;
  targets: number[];
  timeout_seconds: number;
}

export interface AgentConfig {
  apiKey: string;
  serverUrl: string;
  agentName?: string;
  reconnection?: boolean;
  reconnectionAttempts?: number;
  reconnectionDelay?: number;
  timeout?: number;
}
