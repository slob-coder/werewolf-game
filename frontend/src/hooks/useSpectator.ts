import { useEffect, useRef } from 'react'
import { useSocketStore } from '@/stores/socketStore'
import { useGameStore } from '@/stores/gameStore'
import { useAuthStore } from '@/stores/authStore'
import type { GamePhase, Player } from '@/types/game'

/**
 * Hook to manage spectator WebSocket connection for a game.
 * Connects on mount, disconnects on unmount, dispatches events to gameStore.
 */
export function useSpectator(gameId: string | undefined) {
  const token = useAuthStore((s) => s.token)
  const connectSpectator = useSocketStore((s) => s.connectSpectator)
  const disconnect = useSocketStore((s) => s.disconnect)
  const socketStatus = useSocketStore((s) => s.status)
  const socketError = useSocketStore((s) => s.error)

  const {
    setGame,
    updatePhase,
    updatePlayers,
    addSpeech,
    addVote,
    addAction,
    setPlayerDead,
    setWinner,
    setPhaseDeadline,
    setLoading,
    setError,
  } = useGameStore()

  const mountedRef = useRef(true)

  useEffect(() => {
    mountedRef.current = true
    return () => { mountedRef.current = false }
  }, [])

  useEffect(() => {
    if (!gameId || !token) {
      setError(token ? '无效的游戏 ID' : '请先登录')
      return
    }

    setLoading(true)
    const socket = connectSpectator(gameId, token)

    // Full game state snapshot (on initial connect / reconnect)
    socket.on('game.snapshot', (data: Record<string, unknown>) => {
      if (!mountedRef.current) return
      const players = (data.players as Record<string, unknown>[]) ?? []
      setGame({
        gameId: (data.game_id as string) ?? gameId,
        phase: (data.current_phase as GamePhase) ?? 'waiting',
        round: (data.current_round as number) ?? 0,
        players: players.map((p) => ({
          seat: p.seat as number,
          name: (p.agent_name as string) ?? `Agent ${p.seat}`,
          agent_id: p.agent_id as string | undefined,
          status: (p.is_alive as boolean) ? 'alive' : 'dead',
          role: p.role as string | undefined,
          death_round: p.death_round as number | null,
          death_cause: p.death_cause as string | null,
        })),
        winner: (data.winner as string) ?? null,
        win_reason: (data.win_reason as string) ?? null,
        role_config: (data.role_config as Record<string, number>) ?? {},
        speeches: [],
        votes: [],
        actions: [],
        phaseDeadline: null,
      })
    })

    // Phase transitions
    socket.on('phase.change', (data: Record<string, unknown>) => {
      if (!mountedRef.current) return
      updatePhase(
        data.phase as GamePhase,
        data.round as number,
        (data.deadline as number) ?? null,
      )
    })

    // Timer updates
    socket.on('phase.timer', (data: Record<string, unknown>) => {
      if (!mountedRef.current) return
      setPhaseDeadline((data.deadline as number) ?? null)
    })

    // Player speech
    socket.on('player.speech', (data: Record<string, unknown>) => {
      if (!mountedRef.current) return
      addSpeech({
        seat: data.seat as number,
        name: (data.name as string) ?? `Agent ${data.seat}`,
        content: data.content as string,
        round: data.round as number,
        timestamp: data.timestamp as string,
        chain_of_thought: data.chain_of_thought as string | undefined,
      })
    })

    // Vote
    socket.on('vote.cast', (data: Record<string, unknown>) => {
      if (!mountedRef.current) return
      addVote({
        voter_seat: data.voter_seat as number,
        voter_name: (data.voter_name as string) ?? '',
        target_seat: data.target_seat as number,
        target_name: (data.target_name as string) ?? '',
        round: data.round as number,
        timestamp: data.timestamp as string,
      })
    })

    // Player death
    socket.on('player.death', (data: Record<string, unknown>) => {
      if (!mountedRef.current) return
      setPlayerDead(
        data.seat as number,
        data.round as number,
        (data.cause as string) ?? 'unknown',
      )
    })

    // Night actions (god view)
    socket.on('night.action', (data: Record<string, unknown>) => {
      if (!mountedRef.current) return
      addAction({
        round: data.round as number,
        phase: data.phase as string,
        actor_seat: data.actor_seat as number | undefined,
        actor_name: data.actor_name as string | undefined,
        action_type: data.action_type as string,
        target_seat: data.target_seat as number | undefined,
        target_name: data.target_name as string | undefined,
        result: data.result as string | undefined,
        timestamp: data.timestamp as string,
      })
    })

    // Action log (generic)
    socket.on('action.log', (data: Record<string, unknown>) => {
      if (!mountedRef.current) return
      addAction({
        round: data.round as number,
        phase: data.phase as string,
        actor_seat: data.actor_seat as number | undefined,
        actor_name: data.actor_name as string | undefined,
        action_type: data.action_type as string,
        target_seat: data.target_seat as number | undefined,
        target_name: data.target_name as string | undefined,
        result: data.result as string | undefined,
        timestamp: data.timestamp as string,
      })
    })

    // Player list update
    socket.on('players.update', (data: Record<string, unknown>) => {
      if (!mountedRef.current) return
      const players = (data.players as Record<string, unknown>[]) ?? []
      updatePlayers(
        players.map((p) => ({
          seat: p.seat as number,
          name: (p.agent_name as string) ?? `Agent ${p.seat}`,
          agent_id: p.agent_id as string | undefined,
          status: (p.is_alive as boolean) ? 'alive' : 'dead',
          role: p.role as string | undefined,
          death_round: (p.death_round as number) ?? null,
          death_cause: (p.death_cause as string) ?? null,
        } as Player)),
      )
    })

    // Vote result
    socket.on('vote.result', (data: Record<string, unknown>) => {
      if (!mountedRef.current) return
      if (data.eliminated_seat != null) {
        setPlayerDead(
          data.eliminated_seat as number,
          data.round as number,
          'vote',
        )
      }
    })

    // Game end
    socket.on('game.end', (data: Record<string, unknown>) => {
      if (!mountedRef.current) return
      setWinner(
        (data.winner as string) ?? 'unknown',
        (data.reason as string) ?? '',
      )
    })

    return () => {
      disconnect()
    }
  }, [gameId, token, connectSpectator, disconnect, setGame, updatePhase, updatePlayers, addSpeech, addVote, addAction, setPlayerDead, setWinner, setPhaseDeadline, setLoading, setError])

  return { socketStatus, socketError }
}
