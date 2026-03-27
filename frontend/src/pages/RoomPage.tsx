import { useState, useEffect, useRef } from 'react'
import { useParams, Link } from 'react-router-dom'
import { getRoom } from '@/services/api'
import { useSpectator } from '@/hooks/useSpectator'
import { useGameStore } from '@/stores/gameStore'
import type { RoomInfo, RoomStatus } from '@/types/api'
import { ROOM_STATUS_CONFIG } from '@/types/api'
import LoadingSpinner from '@/components/common/LoadingSpinner'
import GameBoard from '@/components/game/GameBoard'
import PhaseIndicator from '@/components/game/PhaseIndicator'
import SpeechBubble from '@/components/game/SpeechBubble'
import VotePanel from '@/components/game/VotePanel'
import NightOverlay from '@/components/game/NightOverlay'
import GodView from '@/components/spectator/GodView'

function StatusBadge({ status, error }: { status: string; error: string | null }) {
  const config: Record<string, { cls: string; text: string }> = {
    connecting: { cls: 'bg-yellow-900/80 text-yellow-300', text: '🔄 连接中...' },
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

export default function RoomPage() {
  const { id } = useParams<{ id: string }>()
  const [room, setRoom] = useState<RoomInfo | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // 游戏状态（观战模式时使用）
  const { socketStatus, socketError } = useSpectator(
    room?.status === 'playing' || room?.status === 'finished' ? room.game_id : undefined
  )
  const game = useGameStore((s) => s.game)
  const resetGame = useGameStore((s) => s.reset)

  // 加载房间信息
  async function loadRoom(roomId: string) {
    try {
      const data = await getRoom(roomId)
      setRoom(data)
      setError(null)
    } catch {
      setError('无法加载房间信息')
    } finally {
      setLoading(false)
    }
  }

  // 初始化 + 轮询（仅在非游戏状态时轮询）
  useEffect(() => {
    if (!id) return
    loadRoom(id)

    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current)
      }
    }
  }, [id])

  // 根据状态控制轮询
  useEffect(() => {
    if (!room || !id) return

    // 游戏进行中或已结束，停止轮询
    if (room.status === 'playing' || room.status === 'finished') {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current)
        pollIntervalRef.current = null
      }
      return
    }

    // 等待中，启动轮询（每 3 秒）
    if (!pollIntervalRef.current) {
      pollIntervalRef.current = setInterval(() => {
        loadRoom(id)
      }, 3000)
    }

    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current)
        pollIntervalRef.current = null
      }
    }
  }, [room?.status, id])

  // 离开页面时重置游戏状态
  useEffect(() => {
    return () => {
      resetGame()
    }
  }, [resetGame])

  // 初始加载
  if (loading) {
    return (
      <div className="min-h-[80vh] flex items-center justify-center">
        <LoadingSpinner text="加载房间信息..." />
      </div>
    )
  }

  if (error || !room) {
    return (
      <div className="min-h-[80vh] flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-400 mb-4">{error ?? '房间不存在'}</p>
          <Link to="/" className="text-werewolf-accent hover:underline">返回首页</Link>
        </div>
      </div>
    )
  }

  // ========== 游戏进行中/已结束：观战布局 ==========
  if ((room.status === 'playing' || room.status === 'finished') && game) {
    const isNight = game.phase.startsWith('night_')
    const currentSpeaker = game.phase === 'day_speech'
      ? game.speeches[game.speeches.length - 1]?.seat ?? null
      : null

    return (
      <div className="h-[calc(100vh-64px)] flex flex-col overflow-hidden">
        {/* 顶部：阶段指示器 */}
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
              to={`/games/${room.game_id}/replay`}
              className="text-xs text-gray-500 hover:text-werewolf-accent flex-shrink-0"
            >
              📼 回放
            </Link>
          </div>
        </div>

        {/* 主区域 */}
        <div className="flex-1 flex overflow-hidden px-4 pb-4 gap-4">
          {/* 左侧：圆桌 + 发言 */}
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

          {/* 右侧：上帝视角 */}
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

        {/* 连接状态指示器 */}
        {socketStatus !== 'connected' && (
          <div className="fixed bottom-4 right-4 z-50">
            <StatusBadge status={socketStatus} error={socketError} />
          </div>
        )}
      </div>
    )
  }

  // ========== 游戏开始前：看板布局 ==========
  const statusConfig = ROOM_STATUS_CONFIG[room.status as RoomStatus] ?? ROOM_STATUS_CONFIG.waiting

  return (
    <div className="max-w-2xl mx-auto py-8">
      <Link to="/" className="text-sm text-gray-400 hover:text-white mb-4 inline-block">
        ← 返回房间列表
      </Link>

      <div className="bg-werewolf-mid border border-gray-700 rounded-lg p-6">
        <div className="flex items-start justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-200">{room.name}</h1>
            <p className="text-sm text-gray-500 mt-1">
              房间 ID: {room.id}
            </p>
          </div>
          <span className={`
            px-3 py-1 rounded-full text-xs font-medium ${statusConfig.color}
            ${room.status === 'waiting' ? 'bg-green-900/50' : ''}
            ${room.status === 'ready' ? 'bg-blue-900/50' : ''}
            ${room.status === 'playing' ? 'bg-yellow-900/50' : ''}
            ${room.status === 'finished' ? 'bg-gray-800' : ''}
            ${room.status === 'cancelled' ? 'bg-red-900/50' : ''}
          `}>
            {statusConfig.icon} {statusConfig.label}
          </span>
        </div>

        <div className="mb-6 grid grid-cols-3 gap-4 text-center">
          <div className="bg-werewolf-dark rounded-lg p-3">
            <div className="text-xl font-bold text-gray-200">
              {room.current_players}/{room.player_count}
            </div>
            <div className="text-xs text-gray-500">玩家数</div>
          </div>
          <div className="bg-werewolf-dark rounded-lg p-3">
            <div className="text-xl font-bold text-gray-200">
              🎭 {room.role_preset ?? 'standard'}
            </div>
            <div className="text-xs text-gray-500">角色配置</div>
          </div>
          <div className="bg-werewolf-dark rounded-lg p-3">
            <div className="text-xl font-bold text-gray-200">
              {statusConfig.icon}
            </div>
            <div className="text-xs text-gray-500">状态</div>
          </div>
        </div>

        {/* Seats */}
        <div>
          <h2 className="text-sm font-semibold text-gray-400 mb-3">座位列表</h2>
          <div className="grid grid-cols-3 gap-2">
            {(room.slots ?? []).map((slot) => (
              <div
                key={slot.seat}
                className={`
                  p-3 rounded-lg text-center transition
                  ${slot.agent_id
                    ? 'bg-werewolf-light/50 border border-blue-800/30'
                    : 'bg-gray-800/30 border border-gray-700/30'
                  }
                `}
              >
                <div className="text-lg font-bold text-gray-300">{slot.seat}</div>
                <div className="text-xs text-gray-400 truncate">
                  {slot.agent_name ?? '空座位'}
                </div>
                {slot.status === 'ready' && (
                  <span className="text-[10px] text-green-400">✓ 已准备</span>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* 游戏开始提示 */}
        {room.status === 'playing' && (
          <div className="mt-6 p-4 bg-yellow-900/30 border border-yellow-700/50 rounded-lg text-center">
            <div className="text-yellow-300">🎮 游戏已开始，正在连接观战...</div>
          </div>
        )}

        {/* Actions */}
        <div className="mt-6 flex gap-3">
          {room.game_id && room.status === 'finished' && (
            <Link
              to={`/games/${room.game_id}`}
              className="px-4 py-2 bg-werewolf-accent rounded-lg font-semibold hover:bg-red-600 transition"
            >
              📺 查看回放
            </Link>
          )}
          <button
            onClick={() => id && loadRoom(id)}
            className="px-4 py-2 bg-gray-700 rounded-lg hover:bg-gray-600 transition"
          >
            🔄 刷新
          </button>
        </div>
      </div>
    </div>
  )
}
