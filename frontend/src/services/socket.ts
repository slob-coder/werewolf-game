import { io, Socket } from 'socket.io-client'

const WS_URL = import.meta.env.VITE_WS_URL || ''

export function createSpectatorSocket(
  gameId: string,
  token: string,
): Socket {
  const socket = io(`${WS_URL}/spectator`, {
    auth: { token, game_id: gameId },
    transports: ['websocket', 'polling'],
    reconnection: true,
    reconnectionAttempts: Infinity,
    reconnectionDelay: 1000,
    reconnectionDelayMax: 10000,
    timeout: 20000,
  })

  return socket
}

export function createLobbySocket(): Socket {
  const socket = io(`${WS_URL}/lobby`, {
    transports: ['websocket', 'polling'],
    reconnection: true,
    reconnectionAttempts: Infinity,
    reconnectionDelay: 2000,
    reconnectionDelayMax: 15000,
  })

  return socket
}
