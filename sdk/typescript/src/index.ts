/**
 * @werewolf-arena/sdk — TypeScript SDK for the Werewolf Arena platform.
 * @packageDocumentation
 */

export { WerewolfAgent } from './agent';
export { ArenaRESTClient } from './client';
export {
  ArenaAPIError,
  ArenaAuthError,
  ArenaConnectionError,
  ArenaError,
  ArenaTimeoutError,
} from './errors';
export {
  type Action,
  type ActionRequestBody,
  type ActionResponse,
  ActionType,
  type AgentConfig,
  type AvailableAction,
  Faction,
  type GameEvent,
  GamePhase,
  type GameState,
  type JoinResponse,
  type PhaseInfo,
  type PlayerInfo,
  type RoleConfig,
  type RoomInfo,
  RoomStatus,
  type SlotInfo,
  type SpeechRecord,
} from './types';
