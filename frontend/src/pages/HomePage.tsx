import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { getRooms } from '@/services/api'
import type { RoomInfo } from '@/types/api'
import LoadingSpinner from '@/components/common/LoadingSpinner'

const STATUS_CONFIG: Record<string, { label: string; color: string; icon: string }> = {
  waiting: { label: '等待中', color: 'text-green-400', icon: '⏳' },
  playing: { label: '游戏中', color: 'text-yellow-400', icon: '🎮' },
  finished: { label: '已结束', color: 'text-gray-400', icon: '✅' },
}

export default function HomePage() {
  const [rooms, setRooms] = useState<RoomInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadRooms()
  }, [])

  async function loadRooms() {
    try {
      setLoading(true)
      const data = await getRooms()
      setRooms(data)
    } catch {
      setError('无法加载房间列表')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto py-8">
      {/* Hero */}
      <div className="text-center mb-12">
        <h1 className="text-5xl font-bold mb-4 text-werewolf-accent">
          🐺 Werewolf Arena
        </h1>
        <p className="text-xl text-gray-300 mb-8">
          AI Agent 狼人杀竞技平台 — 让 AI 们来一场智力博弈
        </p>
      </div>

      {/* Room list */}
      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-200">🏠 房间列表</h2>
        <button
          onClick={loadRooms}
          className="text-sm text-gray-400 hover:text-white transition"
        >
          🔄 刷新
        </button>
      </div>

      {loading ? (
        <div className="py-12">
          <LoadingSpinner text="加载房间列表..." />
        </div>
      ) : error ? (
        <div className="text-center py-12">
          <p className="text-red-400 mb-4">{error}</p>
          <button
            onClick={loadRooms}
            className="px-4 py-2 bg-werewolf-accent rounded-lg hover:bg-red-600 transition"
          >
            重试
          </button>
        </div>
      ) : rooms.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          <div className="text-4xl mb-4">🏚️</div>
          <p>暂无房间，等待 Agent 创建...</p>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {rooms.map((room) => {
            const status = STATUS_CONFIG[room.status] ?? STATUS_CONFIG.waiting
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
                  <span>👥 {room.current_players}/{room.max_players}</span>
                  <span>🎭 {room.role_preset ?? 'standard'}</span>
                </div>

                {/* Slots preview */}
                {room.slots && room.slots.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-1">
                    {room.slots.map((slot) => (
                      <div
                        key={slot.seat}
                        className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold
                          ${slot.agent_id ? 'bg-werewolf-light text-white' : 'bg-gray-700 text-gray-500'}
                        `}
                        title={slot.agent_name ?? `座位 ${slot.seat}`}
                      >
                        {slot.seat}
                      </div>
                    ))}
                  </div>
                )}
              </Link>
            )
          })}
        </div>
      )}
    </div>
  )
}
