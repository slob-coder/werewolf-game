import { useState, useEffect, useCallback, useRef } from 'react'
import type { ReplayData, ReplayEvent, GameState, GamePhase, Player } from '@/types/game'
import { getGameReplay } from '@/services/api'

interface UseReplayReturn {
  replayData: ReplayData | null
  gameState: GameState | null
  currentIndex: number
  totalEvents: number
  isPlaying: boolean
  speed: number
  loading: boolean
  error: string | null
  play: () => void
  pause: () => void
  togglePlay: () => void
  setSpeed: (speed: number) => void
  seekTo: (index: number) => void
  seekToPercent: (pct: number) => void
}

export function useReplay(gameId: string | undefined): UseReplayReturn {
  const [replayData, setReplayData] = useState<ReplayData | null>(null)
  const [gameState, setGameState] = useState<GameState | null>(null)
  const [currentIndex, setCurrentIndex] = useState(0)
  const [isPlaying, setIsPlaying] = useState(false)
  const [speed, setSpeed] = useState(1)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Fetch replay data
  useEffect(() => {
    if (!gameId) return
    setLoading(true)
    getGameReplay(gameId)
      .then((data) => {
        setReplayData(data)
        setLoading(false)
        // Build initial state from players
        if (data.players.length > 0) {
          setGameState({
            gameId: data.game_id,
            phase: 'waiting',
            round: 0,
            players: data.players.map((p) => ({ ...p, status: 'alive' })),
            winner: null,
            win_reason: null,
            role_config: data.role_config,
            speeches: [],
            votes: [],
            actions: [],
            phaseDeadline: null,
          })
        }
      })
      .catch((err) => {
        setError(err.message || '加载回放数据失败')
        setLoading(false)
      })
  }, [gameId])

  // Rebuild game state by replaying events up to currentIndex
  const rebuildState = useCallback(
    (index: number) => {
      if (!replayData) return

      const players: Player[] = replayData.players.map((p) => ({
        ...p,
        status: 'alive' as const,
        death_round: null,
        death_cause: null,
      }))

      let phase: GamePhase = 'waiting'
      let round = 0
      const speeches: GameState['speeches'] = []
      const votes: GameState['votes'] = []
      const actions: GameState['actions'] = []
      let winner: string | null = null
      let winReason: string | null = null

      for (let i = 0; i <= index && i < replayData.events.length; i++) {
        const ev: ReplayEvent = replayData.events[i]
        if (ev.phase) phase = ev.phase as GamePhase
        if (ev.round != null) round = ev.round

        switch (ev.event_type) {
          case 'player.speech':
            speeches.push({
              seat: ev.data.seat as number,
              name: (ev.data.name as string) ?? `Agent ${ev.data.seat}`,
              content: ev.data.content as string,
              round: ev.round,
              timestamp: ev.timestamp,
              chain_of_thought: ev.data.chain_of_thought as string | undefined,
            })
            break
          case 'vote.cast':
            votes.push({
              voter_seat: ev.data.voter_seat as number,
              voter_name: (ev.data.voter_name as string) ?? '',
              target_seat: ev.data.target_seat as number,
              target_name: (ev.data.target_name as string) ?? '',
              round: ev.round,
              timestamp: ev.timestamp,
            })
            break
          case 'player.death': {
            const seat = ev.data.seat as number
            const p = players.find((x) => x.seat === seat)
            if (p) {
              p.status = 'dead'
              p.death_round = ev.round
              p.death_cause = (ev.data.cause as string) ?? 'unknown'
            }
            break
          }
          case 'night.action':
          case 'action.log':
            actions.push({
              round: ev.round,
              phase: ev.phase,
              actor_seat: ev.data.actor_seat as number | undefined,
              actor_name: ev.data.actor_name as string | undefined,
              action_type: ev.data.action_type as string,
              target_seat: ev.data.target_seat as number | undefined,
              target_name: ev.data.target_name as string | undefined,
              result: ev.data.result as string | undefined,
              timestamp: ev.timestamp,
            })
            break
          case 'game.end':
            winner = (ev.data.winner as string) ?? null
            winReason = (ev.data.reason as string) ?? null
            phase = 'game_over'
            break
        }
      }

      setGameState({
        gameId: replayData.game_id,
        phase,
        round,
        players,
        winner,
        win_reason: winReason,
        role_config: replayData.role_config,
        speeches,
        votes,
        actions,
        phaseDeadline: null,
      })
    },
    [replayData],
  )

  // Update state when currentIndex changes
  useEffect(() => {
    rebuildState(currentIndex)
  }, [currentIndex, rebuildState])

  // Playback timer
  useEffect(() => {
    if (isPlaying && replayData) {
      const totalEvents = replayData.events.length
      if (currentIndex >= totalEvents - 1) {
        setIsPlaying(false)
        return
      }
      timerRef.current = setTimeout(() => {
        setCurrentIndex((prev) => Math.min(prev + 1, totalEvents - 1))
      }, 1000 / speed)
    }
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [isPlaying, currentIndex, speed, replayData])

  const play = useCallback(() => setIsPlaying(true), [])
  const pause = useCallback(() => setIsPlaying(false), [])
  const togglePlay = useCallback(() => setIsPlaying((p) => !p), [])

  const seekTo = useCallback(
    (index: number) => {
      if (!replayData) return
      const clamped = Math.max(0, Math.min(index, replayData.events.length - 1))
      setCurrentIndex(clamped)
    },
    [replayData],
  )

  const seekToPercent = useCallback(
    (pct: number) => {
      if (!replayData || replayData.events.length === 0) return
      const index = Math.round(pct * (replayData.events.length - 1))
      setCurrentIndex(index)
    },
    [replayData],
  )

  return {
    replayData,
    gameState,
    currentIndex,
    totalEvents: replayData?.events.length ?? 0,
    isPlaying,
    speed,
    loading,
    error,
    play,
    pause,
    togglePlay,
    setSpeed,
    seekTo,
    seekToPercent,
  }
}
