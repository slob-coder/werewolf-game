import type { Player } from '@/types/game'

interface StatsPanelProps {
  players: Player[]
  round: number
  winner?: string | null
  winReason?: string | null
}

export default function StatsPanel({ players, round, winner, winReason }: StatsPanelProps) {
  const alive = players.filter((p) => p.status === 'alive')
  const dead = players.filter((p) => p.status === 'dead')
  const aliveWolves = alive.filter((p) => p.role === 'werewolf')
  const aliveVillagers = alive.filter((p) => p.role && p.role !== 'werewolf')

  return (
    <div className="space-y-4">
      <h4 className="text-sm font-semibold text-gray-300">📈 游戏统计</h4>

      {/* Winner banner */}
      {winner && (
        <div className={`
          p-3 rounded-lg text-center
          ${winner === 'werewolf'
            ? 'bg-red-950/50 border border-red-800/50'
            : 'bg-green-950/50 border border-green-800/50'
          }
        `}>
          <div className="text-lg font-bold">
            {winner === 'werewolf' ? '🐺 狼人胜利！' : '🛡️ 好人胜利！'}
          </div>
          {winReason && (
            <div className="text-xs text-gray-400 mt-1">{winReason}</div>
          )}
        </div>
      )}

      {/* Survival stats */}
      <div className="grid grid-cols-2 gap-2">
        <StatCard
          label="存活"
          value={alive.length}
          total={players.length}
          color="text-green-400"
          icon="💚"
        />
        <StatCard
          label="阵亡"
          value={dead.length}
          total={players.length}
          color="text-red-400"
          icon="💀"
        />
        <StatCard
          label="狼人存活"
          value={aliveWolves.length}
          total={players.filter((p) => p.role === 'werewolf').length}
          color="text-red-300"
          icon="🐺"
        />
        <StatCard
          label="好人存活"
          value={aliveVillagers.length}
          total={players.filter((p) => p.role && p.role !== 'werewolf').length}
          color="text-green-300"
          icon="🛡️"
        />
      </div>

      {/* Round info */}
      <div className="text-center py-2 bg-werewolf-mid/30 rounded-lg">
        <div className="text-2xl font-bold text-gray-300">{round}</div>
        <div className="text-[10px] text-gray-500 uppercase tracking-wider">当前轮次</div>
      </div>

      {/* Death log */}
      {dead.length > 0 && (
        <div>
          <div className="text-xs text-gray-400 font-semibold mb-1">💀 阵亡名单</div>
          <div className="space-y-1">
            {dead.map((p) => (
              <div key={p.seat} className="text-xs text-gray-500 flex items-center gap-1">
                <span>{p.seat}号</span>
                <span className="text-gray-400">{p.name}</span>
                <span className="text-gray-600">({p.role})</span>
                {p.death_cause && (
                  <span className="text-red-400/60">— {p.death_cause}</span>
                )}
                {p.death_round != null && (
                  <span className="text-gray-600">R{p.death_round}</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function StatCard({
  label,
  value,
  total,
  color,
  icon,
}: {
  label: string
  value: number
  total: number
  color: string
  icon: string
}) {
  return (
    <div className="bg-werewolf-mid/30 rounded-lg p-2 text-center">
      <div className="text-base mb-0.5">{icon}</div>
      <div className={`text-lg font-bold ${color}`}>
        {value}<span className="text-xs text-gray-500">/{total}</span>
      </div>
      <div className="text-[10px] text-gray-500">{label}</div>
    </div>
  )
}
