/**
 * Game-related type definitions.
 */

export type GamePhase =
  | 'waiting'
  | 'role_assignment'
  | 'night_start'
  | 'night_werewolf'
  | 'night_seer'
  | 'night_witch'
  | 'night_hunter'
  | 'night_end'
  | 'day_announcement'
  | 'day_speech'
  | 'day_vote'
  | 'day_vote_result'
  | 'hunter_shoot'
  | 'last_words'
  | 'game_over'

export type RoleName =
  | 'werewolf'
  | 'villager'
  | 'seer'
  | 'witch'
  | 'hunter'
  | 'guard'
  | 'idiot'

export interface Player {
  seat: number
  name: string
  agent_id?: string
  status: 'alive' | 'dead'
  role?: RoleName | string
  death_round?: number | null
  death_cause?: string | null
}

export interface GameState {
  gameId: string
  phase: GamePhase
  round: number
  players: Player[]
  winner?: string | null
  win_reason?: string | null
  role_config?: Record<string, number>
  speeches: SpeechEntry[]
  votes: VoteEntry[]
  actions: ActionLogEntry[]
  phaseDeadline?: number | null
}

export interface SpeechEntry {
  seat: number
  name: string
  content: string
  round: number
  timestamp: string
  chain_of_thought?: string
}

export interface VoteEntry {
  voter_seat: number
  voter_name: string
  target_seat: number
  target_name: string
  round: number
  timestamp: string
}

export interface ActionLogEntry {
  round: number
  phase: string
  actor_seat?: number
  actor_name?: string
  action_type: string
  target_seat?: number
  target_name?: string
  result?: string
  timestamp: string
}

export interface ReplayData {
  game_id: string
  events: ReplayEvent[]
  players: Player[]
  role_config: Record<string, number>
  winner?: string
  win_reason?: string
  total_rounds: number
}

export interface ReplayEvent {
  event_type: string
  round: number
  phase: string
  timestamp: string
  data: Record<string, unknown>
}
