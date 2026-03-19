import type { VoteEntry } from '@/types/game'

interface VoteFlowChartProps {
  votes: VoteEntry[]
  round?: number
}

export default function VoteFlowChart({ votes, round }: VoteFlowChartProps) {
  const displayVotes = round != null
    ? votes.filter((v) => v.round === round)
    : votes

  if (displayVotes.length === 0) {
    return (
      <div className="text-sm text-gray-500 py-4 text-center">
        暂无投票流向数据
      </div>
    )
  }

  // Build flow: voter → target with counts
  const flows = new Map<string, { from: string; to: string; count: number }>()
  for (const v of displayVotes) {
    const key = `${v.voter_seat}->${v.target_seat}`
    const existing = flows.get(key)
    if (existing) {
      existing.count++
    } else {
      flows.set(key, {
        from: `${v.voter_seat}号 ${v.voter_name}`,
        to: `${v.target_seat}号 ${v.target_name}`,
        count: 1,
      })
    }
  }

  // Group by target for visualization
  const targetGroups = new Map<number, { name: string; voters: { seat: number; name: string }[] }>()
  for (const v of displayVotes) {
    const existing = targetGroups.get(v.target_seat)
    if (existing) {
      existing.voters.push({ seat: v.voter_seat, name: v.voter_name })
    } else {
      targetGroups.set(v.target_seat, {
        name: v.target_name,
        voters: [{ seat: v.voter_seat, name: v.voter_name }],
      })
    }
  }

  const sortedGroups = [...targetGroups.entries()].sort((a, b) => b[1].voters.length - a[1].voters.length)

  return (
    <div className="space-y-3">
      <h4 className="text-sm font-semibold text-gray-300 flex items-center gap-2">
        📊 投票流向 {round != null && <span className="text-gray-500">第{round}轮</span>}
      </h4>

      <div className="space-y-3">
        {sortedGroups.map(([seat, group]) => (
          <div key={seat} className="bg-werewolf-mid/30 rounded-lg p-2">
            {/* Target */}
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <span className="text-werewolf-accent font-bold text-sm">🎯 {seat}号</span>
                <span className="text-xs text-gray-400">{group.name}</span>
              </div>
              <span className="text-xs font-bold text-werewolf-accent">
                {group.voters.length} 票
              </span>
            </div>

            {/* Voter arrows */}
            <div className="flex flex-wrap gap-1">
              {group.voters.map((voter, i) => (
                <div
                  key={i}
                  className="text-[10px] bg-werewolf-dark px-2 py-0.5 rounded-full text-gray-400"
                >
                  {voter.seat}号 →
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
