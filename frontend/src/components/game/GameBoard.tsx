import type { Player } from '@/types/game'
import PlayerCard from './PlayerCard'

interface GameBoardProps {
  players: Player[]
  currentSpeaker?: number | null
  className?: string
}

/**
 * Circular seating layout for the werewolf game.
 * Places players in a circle, similar to a real table.
 */
export default function GameBoard({ players, currentSpeaker, className = '' }: GameBoardProps) {
  const count = players.length
  if (count === 0) {
    return (
      <div className={`flex items-center justify-center h-full text-gray-500 ${className}`}>
        等待玩家加入...
      </div>
    )
  }

  // Calculate positions around a circle
  const radius = 38 // percentage from center
  const centerX = 50
  const centerY = 50

  return (
    <div className={`relative w-full aspect-square max-w-lg mx-auto ${className}`}>
      {/* Center area */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 text-center z-0">
        <div className="text-4xl mb-1">🐺</div>
        <div className="text-xs text-gray-500">{count} 名玩家</div>
      </div>

      {/* Players arranged in a circle */}
      {players.map((player, index) => {
        // Start from top (-90 degrees) and go clockwise
        const angle = (index / count) * 360 - 90
        const rad = (angle * Math.PI) / 180
        const x = centerX + radius * Math.cos(rad)
        const y = centerY + radius * Math.sin(rad)

        return (
          <div
            key={player.seat}
            className="absolute -translate-x-1/2 -translate-y-1/2 z-10"
            style={{
              left: `${x}%`,
              top: `${y}%`,
            }}
          >
            <PlayerCard
              player={player}
              isSpeaking={currentSpeaker === player.seat}
            />
          </div>
        )
      })}

      {/* Circular guide ring */}
      <svg className="absolute inset-0 w-full h-full pointer-events-none opacity-10">
        <circle
          cx="50%"
          cy="50%"
          r={`${radius}%`}
          fill="none"
          stroke="white"
          strokeWidth="1"
          strokeDasharray="4,4"
        />
      </svg>
    </div>
  )
}
