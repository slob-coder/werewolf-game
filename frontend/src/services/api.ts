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
  // Register returns UserResponse (no token), so we need to login after
  await api.post('/auth/register', { username, password, email })
  // Auto-login after successful registration
  return login(username, password)
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
  const { data } = await api.get('/agents')
  return data
}

export async function createAgent(name: string, description?: string): Promise<AgentInfo & { api_key: string }> {
  const { data } = await api.post('/agents', { name, description })
  return data
}

export async function deleteAgent(agentId: string): Promise<void> {
  await api.delete(`/agents/${agentId}`)
}

// ── Rooms ─────────────────────────────────────────────

export async function getRooms(page = 1, pageSize = 20): Promise<RoomInfo[]> {
  const { data } = await api.get('/rooms', { params: { status: 'waiting' } })
  return Array.isArray(data) ? data : []
}

export async function getRoom(roomId: string): Promise<RoomInfo> {
  const { data } = await api.get(`/rooms/${roomId}`)
  return data
}

export async function createRoom(name: string, playerCount = 9, rolePreset = 'classic_9p'): Promise<RoomInfo> {
  const { data } = await api.post('/rooms', {
    name,
    config: {
      player_count: playerCount,
      preset: rolePreset,
    },
  })
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
