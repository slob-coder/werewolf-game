import type { VoteEntry } from '@/types/game'

interface VotePanelProps {
  votes: VoteEntry[]
  round?: number
}

export default function VotePanel({ votes, round }: VotePanelProps) {
  // Filter by current round if specified
  const displayVotes = round != null
    ? votes.filter((v) => v.round === round)
    : votes

  if (displayVotes.length === 0) {
    return (
      <div className="text-center text-gray-500 py-4 text-sm">
        暂无投票记录
      </div>
    )
  }

  // Tally votes by target
  const tally = new Map<number, { name: string; voters: string[]; count: number }>()
  for (const v of displayVotes) {
    const existing = tally.get(v.target_seat)
    if (existing) {
      existing.voters.push(`${v.voter_seat}号 ${v.voter_name}`)
      existing.count++
    } else {
      tally.set(v.target_seat, {
        name: v.target_name,
        voters: [`${v.voter_seat}号 ${v.voter_name}`],
        count: 1,
      })
    }
  }

  // Sort by vote count descending
  const sorted = [...tally.entries()].sort((a, b) => b[1].count - a[1].count)
  const maxVotes = sorted[0]?.[1].count ?? 0

  return (
    <div className="space-y-3">
      <h4 className="text-sm font-semibold text-gray-300 flex items-center gap-2">
        🗳️ 投票统计 {round != null && <span className="text-gray-500">第{round}轮</span>}
      </h4>

      {/* Vote bars */}
      {sorted.map(([seat, data]) => (
        <div key={seat} className="space-y-1">
          <div className="flex items-center justify-between text-xs">
            <span className="text-gray-300">{seat}号 {data.name}</span>
            <span className="text-werewolf-accent font-bold">{data.count} 票</span>
          </div>
          <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-werewolf-accent rounded-full transition-all duration-500"
              style={{ width: `${(data.count / maxVotes) * 100}%` }}
            />
          </div>
          <div className="text-[10px] text-gray-500">
            投票者：{data.voters.join('、')}
          </div>
        </div>
      ))}

      {/* Individual vote flow list */}
      <details className="mt-2">
        <summary className="text-xs text-gray-400 cursor-pointer hover:text-gray-300">
          📋 详细投票记录 ({displayVotes.length})
        </summary>
        <div className="mt-2 space-y-1 max-h-40 overflow-y-auto">
          {displayVotes.map((v, i) => (
            <div key={i} className="text-xs text-gray-400 flex items-center gap-1">
              <span className="text-gray-300">{v.voter_seat}号</span>
              <span className="text-gray-500">→</span>
              <span className="text-werewolf-accent">{v.target_seat}号</span>
            </div>
          ))}
        </div>
      </details>
    </div>
  )
}
