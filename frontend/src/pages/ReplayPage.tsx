import { useParams, Link } from 'react-router-dom'
import { useReplay } from '@/hooks/useReplay'
import GameBoard from '@/components/game/GameBoard'
import PhaseIndicator from '@/components/game/PhaseIndicator'
import SpeechBubble from '@/components/game/SpeechBubble'
import VotePanel from '@/components/game/VotePanel'
import NightOverlay from '@/components/game/NightOverlay'
import GodView from '@/components/spectator/GodView'
import TimelineControl from '@/components/spectator/TimelineControl'
import LoadingSpinner from '@/components/common/LoadingSpinner'

export default function ReplayPage() {
  const { id } = useParams<{ id: string }>()
  const {
    gameState,
    currentIndex,
    totalEvents,
    isPlaying,
    speed,
    loading,
    error,
    togglePlay,
    setSpeed,
    seekTo,
  } = useReplay(id)

  if (loading) {
    return (
      <div className="min-h-[80vh] flex items-center justify-center">
        <LoadingSpinner text="加载回放数据..." />
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-[80vh] flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-400 mb-4">{error}</p>
          <Link to="/" className="text-werewolf-accent hover:underline">返回首页</Link>
        </div>
      </div>
    )
  }

  if (!gameState) {
    return (
      <div className="min-h-[80vh] flex items-center justify-center text-gray-400">
        无回放数据
      </div>
    )
  }

  const isNight = gameState.phase.startsWith('night_')
  const currentSpeaker = gameState.phase === 'day_speech'
    ? gameState.speeches[gameState.speeches.length - 1]?.seat ?? null
    : null

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
              phase={gameState.phase}
              round={gameState.round}
            />
          </div>
          <div className="text-xs text-gray-500 flex-shrink-0">
            📼 回放模式
          </div>
        </div>
      </div>

      {/* Main content area */}
      <div className="flex-1 flex overflow-hidden px-4 pb-0 gap-4">
        {/* Left: Game Board + Speeches */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Game Board */}
          <div className="relative flex-shrink-0">
            <GameBoard
              players={gameState.players}
              currentSpeaker={currentSpeaker}
            />
            <NightOverlay isNight={isNight} phase={gameState.phase} />
          </div>

          {/* Vote Panel */}
          {(gameState.phase === 'day_vote' || gameState.phase === 'day_vote_result') && (
            <div className="flex-shrink-0 mt-3 bg-werewolf-mid/50 rounded-lg p-3 border border-gray-700">
              <VotePanel votes={gameState.votes} round={gameState.round} />
            </div>
          )}

          {/* Speech log */}
          <div className="flex-1 mt-3 overflow-y-auto min-h-0 pr-1 scrollbar-thin">
            <h3 className="text-xs font-semibold text-gray-500 mb-2 uppercase tracking-wider sticky top-0 bg-werewolf-dark py-1 z-10">
              💬 发言记录 ({gameState.speeches.length})
            </h3>
            {gameState.speeches.length === 0 ? (
              <div className="text-sm text-gray-600 text-center py-4">暂无发言</div>
            ) : (
              gameState.speeches.map((speech, i) => (
                <SpeechBubble key={i} speech={speech} showCoT />
              ))
            )}
          </div>
        </div>

        {/* Right: God View Panel */}
        <div className="w-72 xl:w-80 flex-shrink-0 bg-werewolf-mid/30 rounded-lg p-3 border border-gray-700/50 overflow-hidden">
          <GodView
            players={gameState.players}
            actions={gameState.actions}
            votes={gameState.votes}
            round={gameState.round}
            winner={gameState.winner}
            winReason={gameState.win_reason}
          />
        </div>
      </div>

      {/* Bottom: Timeline Control */}
      <div className="flex-shrink-0">
        <TimelineControl
          currentIndex={currentIndex}
          totalEvents={totalEvents}
          isPlaying={isPlaying}
          speed={speed}
          onTogglePlay={togglePlay}
          onSeek={seekTo}
          onSpeedChange={setSpeed}
        />
      </div>
    </div>
  )
}
