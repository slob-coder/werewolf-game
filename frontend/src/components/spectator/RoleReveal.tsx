import type { Player } from '@/types/game'

interface RoleRevealProps {
  players: Player[]
}

const ROLE_CONFIG: Record<string, { emoji: string; label: string; team: string; teamColor: string }> = {
  werewolf: { emoji: '🐺', label: '狼人', team: '狼人阵营', teamColor: 'text-red-400' },
  villager: { emoji: '👨‍🌾', label: '村民', team: '好人阵营', teamColor: 'text-green-400' },
  seer: { emoji: '🔮', label: '预言家', team: '好人阵营', teamColor: 'text-green-400' },
  witch: { emoji: '🧙‍♀️', label: '女巫', team: '好人阵营', teamColor: 'text-green-400' },
  hunter: { emoji: '🏹', label: '猎人', team: '好人阵营', teamColor: 'text-green-400' },
  guard: { emoji: '🛡️', label: '守卫', team: '好人阵营', teamColor: 'text-green-400' },
  idiot: { emoji: '🤡', label: '白痴', team: '好人阵营', teamColor: 'text-green-400' },
}

export default function RoleReveal({ players }: RoleRevealProps) {
  if (players.length === 0) {
    return <div className="text-sm text-gray-500">暂无玩家信息</div>
  }

  // Group by team
  const wolves = players.filter((p) => p.role === 'werewolf')
  const goodGuys = players.filter((p) => p.role && p.role !== 'werewolf')
  const unknown = players.filter((p) => !p.role)

  const renderPlayer = (p: Player) => {
    const config = p.role ? ROLE_CONFIG[p.role] : null
    const isDead = p.status === 'dead'

    return (
      <div
        key={p.seat}
        className={`
          flex items-center gap-2 px-2 py-1.5 rounded text-xs
          ${isDead ? 'bg-gray-800/40 opacity-50' : 'bg-werewolf-mid/50'}
        `}
      >
        <span className="w-5 text-center font-bold text-gray-400">{p.seat}</span>
        <span className="text-base">{config?.emoji ?? '❓'}</span>
        <span className={`flex-1 truncate ${isDead ? 'line-through text-gray-500' : 'text-gray-200'}`}>
          {p.name}
        </span>
        <span className={`text-[10px] ${config?.teamColor ?? 'text-gray-500'}`}>
          {config?.label ?? '未知'}
        </span>
        {isDead && (
          <span className="text-[10px] text-red-400">💀</span>
        )}
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <h4 className="text-sm font-semibold text-gray-300 flex items-center gap-2">
        🎭 角色揭示
      </h4>

      {wolves.length > 0 && (
        <div>
          <div className="text-[10px] text-red-400 font-semibold mb-1 uppercase tracking-wider">
            🐺 狼人阵营 ({wolves.filter((p) => p.status === 'alive').length}/{wolves.length})
          </div>
          <div className="space-y-1">{wolves.map(renderPlayer)}</div>
        </div>
      )}

      {goodGuys.length > 0 && (
        <div>
          <div className="text-[10px] text-green-400 font-semibold mb-1 uppercase tracking-wider">
            🛡️ 好人阵营 ({goodGuys.filter((p) => p.status === 'alive').length}/{goodGuys.length})
          </div>
          <div className="space-y-1">{goodGuys.map(renderPlayer)}</div>
        </div>
      )}

      {unknown.length > 0 && (
        <div>
          <div className="text-[10px] text-gray-400 font-semibold mb-1 uppercase tracking-wider">
            ❓ 未知
          </div>
          <div className="space-y-1">{unknown.map(renderPlayer)}</div>
        </div>
      )}
    </div>
  )
}
