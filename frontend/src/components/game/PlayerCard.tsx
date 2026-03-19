import type { Player } from '@/types/game'

interface PlayerCardProps {
  player: Player
  isSpeaking?: boolean
}

const ROLE_EMOJI: Record<string, string> = {
  werewolf: '🐺',
  villager: '👨‍🌾',
  seer: '🔮',
  witch: '🧙‍♀️',
  hunter: '🏹',
  guard: '🛡️',
  idiot: '🤡',
}

const ROLE_LABELS: Record<string, string> = {
  werewolf: '狼人',
  villager: '村民',
  seer: '预言家',
  witch: '女巫',
  hunter: '猎人',
  guard: '守卫',
  idiot: '白痴',
}

export default function PlayerCard({ player, isSpeaking }: PlayerCardProps) {
  const isDead = player.status === 'dead'
  const roleEmoji = player.role ? ROLE_EMOJI[player.role] ?? '❓' : '❓'
  const roleLabel = player.role ? ROLE_LABELS[player.role] ?? player.role : '未知'

  return (
    <div
      className={`
        relative flex flex-col items-center gap-1 p-2 rounded-lg w-20 text-center
        transition-all duration-300
        ${isDead
          ? 'bg-gray-800/60 opacity-50'
          : 'bg-werewolf-mid/80 border border-gray-600'
        }
        ${isSpeaking
          ? 'ring-2 ring-werewolf-accent shadow-lg shadow-werewolf-accent/30 scale-110'
          : ''
        }
      `}
    >
      {/* Seat number badge */}
      <div className="absolute -top-2 -left-2 w-5 h-5 bg-werewolf-light rounded-full flex items-center justify-center text-[10px] font-bold">
        {player.seat}
      </div>

      {/* Role emoji */}
      <div className="text-2xl leading-none">
        {isDead ? '💀' : roleEmoji}
      </div>

      {/* Player name */}
      <div className="text-xs font-medium truncate w-full" title={player.name}>
        {player.name}
      </div>

      {/* Role label */}
      <div className={`text-[10px] ${isDead ? 'text-gray-500 line-through' : 'text-gray-400'}`}>
        {roleLabel}
      </div>

      {/* Speaking indicator */}
      {isSpeaking && !isDead && (
        <div className="absolute -bottom-1 left-1/2 -translate-x-1/2">
          <span className="flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-werewolf-accent opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-werewolf-accent" />
          </span>
        </div>
      )}

      {/* Death overlay */}
      {isDead && (
        <div className="absolute inset-0 bg-black/30 rounded-lg flex items-center justify-center">
          <span className="text-red-400 text-[10px] font-bold">OUT</span>
        </div>
      )}
    </div>
  )
}
