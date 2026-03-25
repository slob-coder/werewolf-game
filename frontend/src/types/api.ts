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

// ── Room Status (unified) ────────────────────────────────────────

export type RoomStatus = 'waiting' | 'ready' | 'playing' | 'finished' | 'cancelled'

export const ROOM_STATUS_CONFIG: Record<RoomStatus, { label: string; color: string; icon: string }> = {
  waiting: { label: '等待中', color: 'text-green-400', icon: '⏳' },
  ready: { label: '满员待开始', color: 'text-blue-400', icon: '✅' },
  playing: { label: '游戏中', color: 'text-yellow-400', icon: '🎮' },
  finished: { label: '已结束', color: 'text-gray-400', icon: '🏁' },
  cancelled: { label: '已取消', color: 'text-red-400', icon: '❌' },
}

export interface RoomInfo {
  id: string
  name: string
  status: RoomStatus
  player_count: number
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
  status: 'empty' | 'occupied' | 'ready' | 'disconnected'
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

// ── Captcha ──────────────────────────────────────────────────────

export interface CaptchaResponse {
  captcha_id: string
  captcha_image: string
}
