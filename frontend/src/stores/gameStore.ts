import { create } from 'zustand'
import type {
  GameState,
  GamePhase,
  Player,
  SpeechEntry,
  VoteEntry,
  ActionLogEntry,
} from '@/types/game'

interface GameStore {
  game: GameState | null
  isLoading: boolean
  error: string | null

  setGame: (game: GameState) => void
  updatePhase: (phase: GamePhase, round: number, deadline?: number | null) => void
  updatePlayers: (players: Player[]) => void
  addSpeech: (speech: SpeechEntry) => void
  addVote: (vote: VoteEntry) => void
  addAction: (action: ActionLogEntry) => void
  setPlayerDead: (seat: number, round: number, cause: string) => void
  setWinner: (winner: string, reason: string) => void
  setPhaseDeadline: (deadline: number | null) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  reset: () => void
}

const initialGame: GameState = {
  gameId: '',
  phase: 'waiting',
  round: 0,
  players: [],
  winner: null,
  win_reason: null,
  role_config: {},
  speeches: [],
  votes: [],
  actions: [],
  phaseDeadline: null,
}

export const useGameStore = create<GameStore>((set) => ({
  game: null,
  isLoading: false,
  error: null,

  setGame: (game) => set({ game, isLoading: false, error: null }),

  updatePhase: (phase, round, deadline) =>
    set((state) => ({
      game: state.game
        ? { ...state.game, phase, round, phaseDeadline: deadline ?? state.game.phaseDeadline }
        : null,
    })),

  updatePlayers: (players) =>
    set((state) => ({
      game: state.game ? { ...state.game, players } : null,
    })),

  addSpeech: (speech) =>
    set((state) => ({
      game: state.game
        ? { ...state.game, speeches: [...state.game.speeches, speech] }
        : null,
    })),

  addVote: (vote) =>
    set((state) => ({
      game: state.game
        ? { ...state.game, votes: [...state.game.votes, vote] }
        : null,
    })),

  addAction: (action) =>
    set((state) => ({
      game: state.game
        ? { ...state.game, actions: [...state.game.actions, action] }
        : null,
    })),

  setPlayerDead: (seat, round, cause) =>
    set((state) => {
      if (!state.game) return state
      const players = state.game.players.map((p) =>
        p.seat === seat
          ? { ...p, status: 'dead' as const, death_round: round, death_cause: cause }
          : p,
      )
      return { game: { ...state.game, players } }
    }),

  setWinner: (winner, reason) =>
    set((state) => ({
      game: state.game
        ? { ...state.game, winner, win_reason: reason, phase: 'game_over' as GamePhase }
        : null,
    })),

  setPhaseDeadline: (deadline) =>
    set((state) => ({
      game: state.game ? { ...state.game, phaseDeadline: deadline } : null,
    })),

  setLoading: (loading) => set({ isLoading: loading }),
  setError: (error) => set({ error }),
  reset: () => set({ game: { ...initialGame }, isLoading: false, error: null }),
}))
