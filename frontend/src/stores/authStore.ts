import { create } from 'zustand'
import { login as apiLogin, register as apiRegister } from '@/services/api'

interface AuthState {
  token: string | null
  username: string | null
  isAuthenticated: boolean
  loading: boolean
  error: string | null

  login: (username: string, password: string) => Promise<void>
  register: (username: string, password: string, captchaId: string, captchaCode: string, email?: string) => Promise<void>
  logout: () => void
  setToken: (token: string, username?: string) => void
  clearError: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  token: localStorage.getItem('token'),
  username: localStorage.getItem('username'),
  isAuthenticated: !!localStorage.getItem('token'),
  loading: false,
  error: null,

  login: async (username: string, password: string) => {
    set({ loading: true, error: null })
    try {
      const result = await apiLogin(username, password)
      localStorage.setItem('token', result.access_token)
      localStorage.setItem('username', username)
      set({
        token: result.access_token,
        username,
        isAuthenticated: true,
        loading: false,
      })
    } catch (err: unknown) {
      const message = (err instanceof Error) ? err.message : '登录失败'
      set({ error: message, loading: false })
      throw err
    }
  },

  register: async (username: string, password: string, captchaId: string, captchaCode: string, email?: string) => {
    set({ loading: true, error: null })
    try {
      const result = await apiRegister(username, password, captchaId, captchaCode, email)
      localStorage.setItem('token', result.access_token)
      localStorage.setItem('username', username)
      set({
        token: result.access_token,
        username,
        isAuthenticated: true,
        loading: false,
      })
    } catch (err: unknown) {
      const message = (err instanceof Error) ? err.message : '注册失败'
      set({ error: message, loading: false })
      throw err
    }
  },

  logout: () => {
    localStorage.removeItem('token')
    localStorage.removeItem('username')
    set({ token: null, username: null, isAuthenticated: false })
  },

  setToken: (token: string, username?: string) => {
    localStorage.setItem('token', token)
    if (username) localStorage.setItem('username', username)
    set({ token, username: username ?? null, isAuthenticated: true })
  },

  clearError: () => set({ error: null }),
}))
