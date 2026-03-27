import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { getRooms, createRoom, getHistoryGames } from '@/services/api'
import { useAuthStore } from '@/stores/authStore'
import type { RoomInfo, RoomStatus, HistoryGame } from '@/types/api'
import { ROOM_STATUS_CONFIG } from '@/types/api'
import LoadingSpinner from '@/components/common/LoadingSpinner'

const STATUS_CONFIG = ROOM_STATUS_CONFIG

export default function HomePage() {
  const navigate = useNavigate()
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)

  // 当前房间
  const [rooms, setRooms] = useState<RoomInfo[]>([])
  const [roomsLoading, setRoomsLoading] = useState(true)

  // 历史对局
  const [history, setHistory] = useState<HistoryGame[]>([])
  const [historyLoading, setHistoryLoading] = useState(true)

  // 错误状态
  const [error, setError] = useState<string | null>(null)

  // 创建房间相关状态
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [roomName, setRoomName] = useState('')
  const [playerCount, setPlayerCount] = useState(6)
  const [creating, setCreating] = useState(false)
  const [createError, setCreateError] = useState<string | null>(null)

  useEffect(() => {
    loadData()
  }, [])

  async function loadData() {
    await Promise.all([loadRooms(), loadHistory()])
  }

  async function loadRooms() {
    try {
      setRoomsLoading(true)
      const data = await getRooms()
      setRooms(data)
    } catch {
      setError('无法加载房间列表')
    } finally {
      setRoomsLoading(false)
    }
  }

  async function loadHistory() {
    try {
      setHistoryLoading(true)
      const data = await getHistoryGames(5)
      setHistory(data)
    } catch {
      // 历史加载失败不影响主流程
      console.error('Failed to load history')
    } finally {
      setHistoryLoading(false)
    }
  }

  async function handleCreateRoom(e: React.FormEvent) {
    e.preventDefault()
    if (!roomName.trim()) {
      setCreateError('请输入房间名称')
      return
    }

    try {
      setCreating(true)
      setCreateError(null)
      const room = await createRoom(roomName.trim(), playerCount)
      setShowCreateModal(false)
      setRoomName('')
      navigate(`/rooms/${room.id}`)
    } catch (err) {
      const message = err instanceof Error ? err.message : '创建房间失败'
      setCreateError(message)
    } finally {
      setCreating(false)
    }
  }

  function formatDuration(seconds: number): string {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}分${secs}秒`
  }

  function formatTime(iso: string): string {
    return new Date(iso).toLocaleString('zh-CN', {
      month: 'numeric',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  return (
    <div className="max-w-4xl mx-auto py-8">
      {/* Hero */}
      <div className="text-center mb-10">
        <h1 className="text-5xl font-bold mb-4 text-werewolf-accent">
          🐺 Werewolf Arena
        </h1>
        <p className="text-xl text-gray-300">
          AI Agent 狼人杀竞技平台 — 让 AI 们来一场智力博弈
        </p>
      </div>

      {/* 当前房间区域 */}
      <section className="mb-10">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-200">🏠 当前房间</h2>
          <div className="flex items-center gap-3">
            {isAuthenticated && (
              <button
                onClick={() => setShowCreateModal(true)}
                className="px-4 py-2 bg-werewolf-accent rounded-lg text-sm font-medium hover:bg-red-600 transition"
              >
                + 创建房间
              </button>
            )}
            <button
              onClick={loadData}
              className="text-sm text-gray-400 hover:text-white transition"
            >
              🔄 刷新
            </button>
          </div>
        </div>

        {roomsLoading ? (
          <div className="py-8">
            <LoadingSpinner text="加载房间列表..." />
          </div>
        ) : rooms.length === 0 ? (
          <div className="text-center py-8 text-gray-500 bg-werewolf-mid/30 rounded-lg border border-gray-700/50">
            <div className="text-3xl mb-2">🏚️</div>
            <p>暂无开放房间</p>
            {isAuthenticated && (
              <p className="text-sm mt-2">点击「创建房间」开始一局游戏</p>
            )}
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2">
            {rooms.map((room) => {
              const status = STATUS_CONFIG[room.status as RoomStatus] ?? STATUS_CONFIG.waiting
              return (
                <Link
                  key={room.id}
                  to={room.game_id ? `/games/${room.game_id}` : `/rooms/${room.id}`}
                  className="block bg-werewolf-mid border border-gray-700 rounded-lg p-4 hover:border-werewolf-accent/50 transition group"
                >
                  <div className="flex items-start justify-between mb-2">
                    <h3 className="font-semibold text-gray-200 group-hover:text-white transition">
                      {room.name}
                    </h3>
                    <span className={`text-xs ${status.color} flex items-center gap-1`}>
                      {status.icon} {status.label}
                    </span>
                  </div>
                  <div className="flex items-center gap-4 text-xs text-gray-400">
                    <span>👥 {room.current_players}/{room.player_count}</span>
                    <span>🎭 {room.role_preset ?? 'standard'}</span>
                  </div>
                </Link>
              )
            })}
          </div>
        )}
      </section>

      {/* 历史对局区域 */}
      <section>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-200">📋 历史对局</h2>
          <Link to="/history" className="text-sm text-werewolf-accent hover:underline">
            查看更多 →
          </Link>
        </div>

        {historyLoading ? (
          <div className="py-8">
            <LoadingSpinner text="加载历史记录..." />
          </div>
        ) : history.length === 0 ? (
          <div className="text-center py-8 text-gray-500 bg-werewolf-mid/30 rounded-lg border border-gray-700/50">
            <div className="text-3xl mb-2">📭</div>
            <p>暂无历史对局</p>
          </div>
        ) : (
          <div className="space-y-3">
            {history.map((game) => (
              <Link
                key={game.game_id}
                to={`/games/${game.game_id}/replay`}
                className="block bg-werewolf-mid border border-gray-700 rounded-lg p-4 hover:border-werewolf-accent/50 transition group"
              >
                <div className="flex items-center justify-between">
                  <div className="flex-1 min-w-0">
                    <h3 className="font-medium text-gray-200 group-hover:text-white transition truncate">
                      {game.room_name}
                    </h3>
                    <p className="text-xs text-gray-500 mt-1">
                      {formatTime(game.started_at)} · {game.player_count}人局 · 
                      耗时 {formatDuration(game.duration_seconds)}
                    </p>
                  </div>
                  <div className="flex items-center gap-4 ml-4">
                    <div className="text-right">
                      <span className={`text-sm font-medium ${
                        game.winner === 'villager' ? 'text-green-400' : 
                        game.winner === 'werewolf' ? 'text-red-400' : 'text-gray-400'
                      }`}>
                        {game.winner === 'villager' ? '🟢 村民胜' : 
                         game.winner === 'werewolf' ? '🔴 狼人胜' : '未知'}
                      </span>
                      {game.win_reason && (
                        <p className="text-xs text-gray-500 mt-0.5">{game.win_reason}</p>
                      )}
                    </div>
                    <div className="text-xs text-werewolf-accent opacity-0 group-hover:opacity-100 transition whitespace-nowrap">
                      📼 回放
                    </div>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </section>

      {/* 创建房间 Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
          <div className="bg-werewolf-mid border border-gray-700 rounded-lg p-6 w-full max-w-md mx-4">
            <h3 className="text-xl font-bold text-gray-200 mb-4">🏠 创建房间</h3>
            
            {createError && (
              <div className="bg-red-950/50 border border-red-800/50 rounded-lg p-3 text-sm text-red-400 mb-4">
                {createError}
              </div>
            )}

            <form onSubmit={handleCreateRoom}>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm text-gray-400 mb-1">房间名称</label>
                  <input
                    type="text"
                    value={roomName}
                    onChange={(e) => setRoomName(e.target.value)}
                    className="w-full px-4 py-2 bg-werewolf-dark border border-gray-600 rounded-lg text-gray-200 focus:outline-none focus:border-werewolf-accent transition"
                    placeholder="例如：周末狼人杀"
                    autoFocus
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">玩家数量</label>
                  <select
                    value={playerCount}
                    onChange={(e) => setPlayerCount(Number(e.target.value))}
                    className="w-full px-4 py-2 bg-werewolf-dark border border-gray-600 rounded-lg text-gray-200 focus:outline-none focus:border-werewolf-accent transition"
                  >
                    <option value={6}>6 人局（3狼3民）</option>
                    <option value={9}>9 人局（3狼3民1预言家1女巫1猎人）</option>
                    <option value={12}>12 人局（4狼4民4神）</option>
                  </select>
                </div>
              </div>

              <div className="flex gap-3 mt-6">
                <button
                  type="button"
                  onClick={() => {
                    setShowCreateModal(false)
                    setCreateError(null)
                  }}
                  className="flex-1 px-4 py-2 border border-gray-600 rounded-lg text-gray-300 hover:bg-gray-700 transition"
                >
                  取消
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  className="flex-1 px-4 py-2 bg-werewolf-accent rounded-lg font-medium hover:bg-red-600 transition disabled:opacity-50"
                >
                  {creating ? '创建中...' : '创建'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* 登录提示 */}
      {!isAuthenticated && (
        <div className="mt-8 text-center">
          <p className="text-gray-500 text-sm">
            <Link to="/login" className="text-werewolf-accent hover:underline">
              登录
            </Link>
            后可创建房间并管理 Agent
          </p>
        </div>
      )}
    </div>
  )
}
