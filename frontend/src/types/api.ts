/**
 * API response type definitions.
 */

export interface ApiResponse<T = unknown> {
  status: string
  data?: T
  message?: string
}

export interface HealthResponse {
  status: string
  service: string
  version?: string
}

export interface AuthTokens {
  access_token: string
  token_type: string
}

export interface UserInfo {
  id: string
  username: string
  email?: string
  created_at: string
}

export interface AgentInfo {
  id: string
  name: string
  description?: string
  owner_id: string
  created_at: string
  games_played?: number
  win_rate?: number
}

export interface RoomInfo {
  id: string
  name: string
  status: 'waiting' | 'playing' | 'finished'
  max_players: number
  current_players: number
  role_preset?: string
  created_by: string
  created_at: string
  game_id?: string
  slots: RoomSlot[]
}

export interface RoomSlot {
  seat: number
  agent_id?: string
  agent_name?: string
  ready: boolean
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}
