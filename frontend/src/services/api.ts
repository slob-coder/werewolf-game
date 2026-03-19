import axios from 'axios'
import type {
  AuthTokens,
  UserInfo,
  AgentInfo,
  RoomInfo,
  PaginatedResponse,
} from '@/types/api'
import type { ReplayData } from '@/types/game'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Attach JWT automatically
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Handle 401 globally
api.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      // Only redirect if not already on auth pages
      if (!window.location.pathname.startsWith('/login') &&
          !window.location.pathname.startsWith('/register')) {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  },
)

// ── Auth ──────────────────────────────────────────────

export async function register(username: string, password: string, email?: string): Promise<AuthTokens> {
  const { data } = await api.post('/auth/register', { username, password, email })
  return data
}

export async function login(username: string, password: string): Promise<AuthTokens> {
  const { data } = await api.post('/auth/login', { username, password })
  return data
}

export async function getMe(): Promise<UserInfo> {
  const { data } = await api.get('/auth/me')
  return data
}

// ── Agents ────────────────────────────────────────────

export async function getMyAgents(): Promise<AgentInfo[]> {
  const { data } = await api.get('/auth/agents')
  return data
}

export async function createAgent(name: string, description?: string): Promise<AgentInfo & { api_key: string }> {
  const { data } = await api.post('/auth/agents', { name, description })
  return data
}

export async function deleteAgent(agentId: string): Promise<void> {
  await api.delete(`/auth/agents/${agentId}`)
}

// ── Rooms ─────────────────────────────────────────────

export async function getRooms(page = 1, pageSize = 20): Promise<PaginatedResponse<RoomInfo>> {
  const { data } = await api.get('/rooms', { params: { page, page_size: pageSize } })
  return data
}

export async function getRoom(roomId: string): Promise<RoomInfo> {
  const { data } = await api.get(`/rooms/${roomId}`)
  return data
}

export async function createRoom(name: string, maxPlayers = 9, rolePreset = 'standard_9'): Promise<RoomInfo> {
  const { data } = await api.post('/rooms', { name, max_players: maxPlayers, role_preset: rolePreset })
  return data
}

// ── Games ─────────────────────────────────────────────

export async function getGameState(gameId: string): Promise<Record<string, unknown>> {
  const { data } = await api.get(`/games/${gameId}`)
  return data
}

export async function getGameReplay(gameId: string): Promise<ReplayData> {
  const { data } = await api.get(`/games/${gameId}/replay`)
  return data
}

// ── Stats ─────────────────────────────────────────────

export async function getLeaderboard(): Promise<Record<string, unknown>[]> {
  const { data } = await api.get('/stats/leaderboard')
  return data
}

export async function getAgentStats(agentId: string): Promise<Record<string, unknown>> {
  const { data } = await api.get(`/stats/agents/${agentId}`)
  return data
}

// ── Roles ─────────────────────────────────────────────

export async function getRoles(): Promise<Record<string, unknown>[]> {
  const { data } = await api.get('/roles')
  return data
}

export async function getRolePresets(): Promise<Record<string, unknown>[]> {
  const { data } = await api.get('/roles/presets')
  return data
}

export default api
