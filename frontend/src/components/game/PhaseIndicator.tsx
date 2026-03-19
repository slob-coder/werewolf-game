import { useEffect, useState } from 'react'
import type { GamePhase } from '@/types/game'

interface PhaseIndicatorProps {
  phase: GamePhase
  round: number
  deadline?: number | null
}

const PHASE_INFO: Record<string, { label: string; icon: string; color: string }> = {
  waiting: { label: '等待中', icon: '⏳', color: 'text-gray-400' },
  role_assignment: { label: '分配角色', icon: '🎭', color: 'text-yellow-400' },
  night_start: { label: '夜晚开始', icon: '🌙', color: 'text-blue-400' },
  night_werewolf: { label: '狼人行动', icon: '🐺', color: 'text-red-400' },
  night_seer: { label: '预言家查验', icon: '🔮', color: 'text-purple-400' },
  night_witch: { label: '女巫行动', icon: '🧙‍♀️', color: 'text-green-400' },
  night_hunter: { label: '猎人行动', icon: '🏹', color: 'text-orange-400' },
  night_end: { label: '天亮了', icon: '🌅', color: 'text-yellow-300' },
  day_announcement: { label: '公布信息', icon: '📢', color: 'text-yellow-400' },
  day_speech: { label: '玩家发言', icon: '🗣️', color: 'text-blue-300' },
  day_vote: { label: '投票阶段', icon: '🗳️', color: 'text-orange-400' },
  day_vote_result: { label: '投票结果', icon: '📊', color: 'text-orange-300' },
  hunter_shoot: { label: '猎人开枪', icon: '💥', color: 'text-red-500' },
  last_words: { label: '遗言', icon: '💬', color: 'text-gray-300' },
  game_over: { label: '游戏结束', icon: '🏆', color: 'text-yellow-500' },
}

function isNightPhase(phase: string): boolean {
  return phase.startsWith('night_')
}

export default function PhaseIndicator({ phase, round, deadline }: PhaseIndicatorProps) {
  const [countdown, setCountdown] = useState<number | null>(null)

  useEffect(() => {
    if (!deadline) {
      setCountdown(null)
      return
    }

    const updateCountdown = () => {
      const remaining = Math.max(0, Math.ceil((deadline - Date.now()) / 1000))
      setCountdown(remaining)
    }

    updateCountdown()
    const interval = setInterval(updateCountdown, 1000)
    return () => clearInterval(interval)
  }, [deadline])

  const info = PHASE_INFO[phase] ?? { label: phase, icon: '❓', color: 'text-gray-400' }
  const isNight = isNightPhase(phase)

  return (
    <div
      className={`
        flex items-center justify-between px-4 py-3 rounded-lg
        ${isNight ? 'bg-indigo-950/60 border border-indigo-800/50' : 'bg-werewolf-mid border border-gray-700'}
      `}
    >
      <div className="flex items-center gap-3">
        <span className="text-2xl">{info.icon}</span>
        <div>
          <div className={`font-semibold ${info.color}`}>{info.label}</div>
          <div className="text-xs text-gray-500">
            第 {round} 轮 {isNight ? '🌙 夜晚' : '☀️ 白天'}
          </div>
        </div>
      </div>

      {countdown !== null && countdown > 0 && (
        <div className={`text-2xl font-mono font-bold ${countdown <= 10 ? 'text-red-400 animate-pulse' : 'text-gray-300'}`}>
          ⏱️ {countdown}s
        </div>
      )}
    </div>
  )
}
