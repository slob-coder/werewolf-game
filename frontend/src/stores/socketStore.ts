import { create } from 'zustand'
import type { Socket } from 'socket.io-client'
import { createSpectatorSocket } from '@/services/socket'

type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error'

interface SocketStore {
  socket: Socket | null
  status: ConnectionStatus
  error: string | null

  connectSpectator: (gameId: string, token: string) => Socket
  disconnect: () => void
  setStatus: (status: ConnectionStatus) => void
  setError: (error: string | null) => void
}

export const useSocketStore = create<SocketStore>((set, get) => ({
  socket: null,
  status: 'disconnected',
  error: null,

  connectSpectator: (gameId: string, token: string) => {
    // Disconnect existing socket first
    const current = get().socket
    if (current) {
      current.disconnect()
    }

    set({ status: 'connecting', error: null })

    const socket = createSpectatorSocket(gameId, token)

    socket.on('connect', () => {
      set({ status: 'connected', error: null })
    })

    socket.on('disconnect', (reason) => {
      if (reason === 'io server disconnect') {
        set({ status: 'disconnected', error: '被服务器断开连接' })
      } else {
        set({ status: 'disconnected' })
      }
    })

    socket.on('connect_error', (err) => {
      set({ status: 'error', error: err.message })
    })

    socket.on('reconnect_attempt', () => {
      set({ status: 'connecting' })
    })

    socket.on('reconnect', () => {
      set({ status: 'connected', error: null })
    })

    set({ socket })
    return socket
  },

  disconnect: () => {
    const { socket } = get()
    if (socket) {
      socket.disconnect()
    }
    set({ socket: null, status: 'disconnected', error: null })
  },

  setStatus: (status) => set({ status }),
  setError: (error) => set({ error }),
}))
