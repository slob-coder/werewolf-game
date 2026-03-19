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
