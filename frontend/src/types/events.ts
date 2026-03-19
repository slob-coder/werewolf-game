/**
 * WebSocket event type definitions.
 */

export interface GameEvent {
  event_type: string
  game_id: string
  timestamp: string
  round: number
  phase: string
  data: Record<string, unknown>
  visibility: 'public' | 'private' | 'role'
}

/** Spectator-specific events received via /spectator namespace */
export type SpectatorEventType =
  | 'game.snapshot'
  | 'game.start'
  | 'game.end'
  | 'phase.change'
  | 'player.speech'
  | 'player.death'
  | 'vote.cast'
  | 'vote.result'
  | 'night.action'
  | 'action.log'
  | 'phase.timer'
