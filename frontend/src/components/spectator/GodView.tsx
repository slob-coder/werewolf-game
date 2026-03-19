import type { Player, ActionLogEntry, VoteEntry } from '@/types/game'
import RoleReveal from './RoleReveal'
import ActionLog from './ActionLog'
import VoteFlowChart from './VoteFlowChart'
import StatsPanel from './StatsPanel'

interface GodViewProps {
  players: Player[]
  actions: ActionLogEntry[]
  votes: VoteEntry[]
  round: number
  winner?: string | null
  winReason?: string | null
}

export default function GodView({
  players,
  actions,
  votes,
  round,
  winner,
  winReason,
}: GodViewProps) {
  return (
    <div className="space-y-6 h-full overflow-y-auto pr-1 scrollbar-thin">
      {/* Stats Panel */}
      <StatsPanel
        players={players}
        round={round}
        winner={winner}
        winReason={winReason}
      />

      {/* Role Reveal */}
      <RoleReveal players={players} />

      {/* Action Log */}
      <ActionLog actions={actions} />

      {/* Vote Flow Chart */}
      <VoteFlowChart votes={votes} round={round} />
    </div>
  )
}
