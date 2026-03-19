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

export interface Player {
  seat: number
  name: string
  status: 'alive' | 'dead'
  role?: string
}

export interface GameState {
  gameId: string
  phase: GamePhase
  round: number
  players: Player[]
}
