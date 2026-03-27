import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { getHistoryGames } from '@/services/api'
import type { HistoryGame } from '@/types/api'
import LoadingSpinner from '@/components/common/LoadingSpinner'

export default function HistoryPage() {
  const [games, setGames] = useState<HistoryGame[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadHistory()
  }, [])

  async function loadHistory() {
    try {
      setLoading(true)
      const data = await getHistoryGames(50)
      setGames(data)
    } catch {
      setError('加载历史记录失败')
    } finally {
      setLoading(false)
    }
  }

  function formatDuration(seconds: number): string {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}分${secs}秒`
  }

  function formatTime(iso: string): string {
    return new Date(iso).toLocaleString('zh-CN', {
      year: 'numeric',
      month: 'numeric',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  if (loading) {
    return (
      <div className="min-h-[80vh] flex items-center justify-center">
        <LoadingSpinner text="加载历史记录..." />
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-[80vh] flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-400 mb-4">{error}</p>
          <button
            onClick={loadHistory}
            className="px-4 py-2 bg-werewolf-accent rounded-lg hover:bg-red-600 transition"
          >
            重试
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-200">📋 历史对局</h1>
        <Link to="/" className="text-sm text-gray-400 hover:text-white transition">
          ← 返回首页
        </Link>
      </div>

      {games.length === 0 ? (
        <div className="text-center py-16 text-gray-500">
          <div className="text-5xl mb-4">📭</div>
          <p>暂无历史对局记录</p>
          <Link to="/" className="text-werewolf-accent hover:underline text-sm mt-2 inline-block">
            去创建一个房间开始游戏
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          {games.map((game) => (
            <Link
              key={game.game_id}
              to={`/games/${game.game_id}/replay`}
              className="block bg-werewolf-mid border border-gray-700 rounded-lg p-4 hover:border-werewolf-accent/50 transition group"
            >
              <div className="flex items-center justify-between">
                <div className="flex-1 min-w-0">
                  <h3 className="font-medium text-gray-200 group-hover:text-white transition">
                    {game.room_name}
                  </h3>
                  <p className="text-xs text-gray-500 mt-1">
                    {formatTime(game.started_at)} · {game.player_count}人局 · 
                    耗时 {formatDuration(game.duration_seconds)}
                  </p>
                  {/* 角色配置 */}
                  <div className="flex gap-2 mt-2 text-xs text-gray-500">
                    {Object.entries(game.role_config || {}).map(([role, count]) => (
                      <span key={role}>{role}: {count}</span>
                    ))}
                  </div>
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
                      <p className="text-xs text-gray-500 mt-0.5 max-w-[200px] text-right">
                        {game.win_reason}
                      </p>
                    )}
                  </div>
                  <div className="px-3 py-1.5 bg-werewolf-accent/20 text-werewolf-accent text-xs rounded-lg group-hover:bg-werewolf-accent group-hover:text-white transition">
                    📼 回放
                  </div>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
