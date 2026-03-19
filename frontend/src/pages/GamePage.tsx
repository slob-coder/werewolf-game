import { useParams, Link } from 'react-router-dom'
import { useSpectator } from '@/hooks/useSpectator'
import { useGameStore } from '@/stores/gameStore'
import GameBoard from '@/components/game/GameBoard'
import PhaseIndicator from '@/components/game/PhaseIndicator'
import SpeechBubble from '@/components/game/SpeechBubble'
import VotePanel from '@/components/game/VotePanel'
import NightOverlay from '@/components/game/NightOverlay'
import GodView from '@/components/spectator/GodView'
import LoadingSpinner from '@/components/common/LoadingSpinner'

function StatusBadge({ status, error }: { status: string; error: string | null }) {
  const config: Record<string, { cls: string; text: string }> = {
    connecting: { cls: 'bg-yellow-900/80 text-yellow-300', text: '🔄 重连中...' },
    error: { cls: 'bg-red-900/80 text-red-300', text: `❌ ${error ?? '连接错误'}` },
    disconnected: { cls: 'bg-gray-800/80 text-gray-400', text: '⚡ 连接已断开' },
  }
  const c = config[status] ?? config.disconnected
  return (
    <div className={`px-3 py-2 rounded-lg text-xs font-medium shadow-lg ${c.cls}`}>
      {c.text}
    </div>
  )
}

export default function GamePage() {
  const { id } = useParams<{ id: string }>()
  const { socketStatus, socketError } = useSpectator(id)
  const game = useGameStore((s) => s.game)
  const isLoading = useGameStore((s) => s.isLoading)
  const gameError = useGameStore((s) => s.error)

  const isNight = game?.phase.startsWith('night_') ?? false
  const currentSpeaker = game?.phase === 'day_speech'
    ? game.speeches[game.speeches.length - 1]?.seat ?? null
    : null

  if (isLoading || socketStatus === 'connecting') {
    return (
      <div className="min-h-[80vh] flex items-center justify-center">
        <LoadingSpinner text="连接游戏中..." />
      </div>
    )
  }

  if (gameError || socketError) {
    return (
      <div className="min-h-[80vh] flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-400 mb-4">{gameError ?? socketError}</p>
          <Link to="/" className="text-werewolf-accent hover:underline">返回首页</Link>
        </div>
      </div>
    )
  }

  if (!game) {
    return (
      <div className="min-h-[80vh] flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-400 mb-4">等待游戏数据...</p>
          <div className="text-xs text-gray-500">连接状态: {socketStatus}</div>
        </div>
      </div>
    )
  }

  return (
    <div className="h-[calc(100vh-64px)] flex flex-col overflow-hidden">
      {/* Top: Phase indicator */}
      <div className="flex-shrink-0 px-4 pt-3 pb-2">
        <div className="flex items-center justify-between gap-4">
          <Link to="/" className="text-sm text-gray-500 hover:text-white flex-shrink-0">
            ← 返回
          </Link>
          <div className="flex-1">
            <PhaseIndicator
              phase={game.phase}
              round={game.round}
              deadline={game.phaseDeadline}
            />
          </div>
          <Link
            to={`/games/${id}/replay`}
            className="text-xs text-gray-500 hover:text-werewolf-accent flex-shrink-0"
          >
            📼 回放
          </Link>
        </div>
      </div>

      {/* Main content area */}
      <div className="flex-1 flex overflow-hidden px-4 pb-4 gap-4">
        {/* Left: Game Board + Speeches */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Game Board */}
          <div className="relative flex-shrink-0">
            <GameBoard
              players={game.players}
              currentSpeaker={currentSpeaker}
            />
            <NightOverlay isNight={isNight} phase={game.phase} />
          </div>

          {/* Vote Panel (during vote phase) */}
          {(game.phase === 'day_vote' || game.phase === 'day_vote_result') && (
            <div className="flex-shrink-0 mt-3 bg-werewolf-mid/50 rounded-lg p-3 border border-gray-700">
              <VotePanel votes={game.votes} round={game.round} />
            </div>
          )}

          {/* Speech log */}
          <div className="flex-1 mt-3 overflow-y-auto min-h-0 pr-1 scrollbar-thin">
            <h3 className="text-xs font-semibold text-gray-500 mb-2 uppercase tracking-wider sticky top-0 bg-werewolf-dark py-1 z-10">
              💬 发言记录 ({game.speeches.length})
            </h3>
            {game.speeches.length === 0 ? (
              <div className="text-sm text-gray-600 text-center py-4">暂无发言</div>
            ) : (
              game.speeches.map((speech, i) => (
                <SpeechBubble key={i} speech={speech} showCoT />
              ))
            )}
          </div>
        </div>

        {/* Right: God View Panel */}
        <div className="w-72 xl:w-80 flex-shrink-0 bg-werewolf-mid/30 rounded-lg p-3 border border-gray-700/50 overflow-hidden">
          <GodView
            players={game.players}
            actions={game.actions}
            votes={game.votes}
            round={game.round}
            winner={game.winner}
            winReason={game.win_reason}
          />
        </div>
      </div>

      {/* Connection status indicator */}
      {socketStatus !== 'connected' && (
        <div className="fixed bottom-4 right-4 z-50">
          <StatusBadge status={socketStatus} error={socketError} />
        </div>
      )}
    </div>
  )
}
