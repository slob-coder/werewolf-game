import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { getRoom } from '@/services/api'
import type { RoomInfo } from '@/types/api'
import LoadingSpinner from '@/components/common/LoadingSpinner'

export default function RoomPage() {
  const { id } = useParams<{ id: string }>()
  const [room, setRoom] = useState<RoomInfo | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    loadRoom(id)
  }, [id])

  async function loadRoom(roomId: string) {
    try {
      setLoading(true)
      const data = await getRoom(roomId)
      setRoom(data)
    } catch {
      setError('无法加载房间信息')
    } finally {
      setLoading(false)
    }
  }

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
            px-3 py-1 rounded-full text-xs font-medium
            ${room.status === 'waiting' ? 'bg-green-900/50 text-green-400' : ''}
            ${room.status === 'playing' ? 'bg-yellow-900/50 text-yellow-400' : ''}
            ${room.status === 'finished' ? 'bg-gray-800 text-gray-400' : ''}
          `}>
            {room.status === 'waiting' ? '等待中' : room.status === 'playing' ? '游戏中' : '已结束'}
          </span>
        </div>

        <div className="mb-6 grid grid-cols-3 gap-4 text-center">
          <div className="bg-werewolf-dark rounded-lg p-3">
            <div className="text-xl font-bold text-gray-200">
              {room.current_players}/{room.max_players}
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
              {room.status === 'playing' ? '🎮' : room.status === 'finished' ? '✅' : '⏳'}
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
                {slot.ready && (
                  <span className="text-[10px] text-green-400">✓ 已准备</span>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Actions */}
        <div className="mt-6 flex gap-3">
          {room.game_id && (
            <Link
              to={`/games/${room.game_id}`}
              className="px-4 py-2 bg-werewolf-accent rounded-lg font-semibold hover:bg-red-600 transition"
            >
              📺 进入观战
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
