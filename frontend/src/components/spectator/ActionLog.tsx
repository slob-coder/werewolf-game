import { useRef, useEffect } from 'react'
import type { ActionLogEntry } from '@/types/game'

interface ActionLogProps {
  actions: ActionLogEntry[]
}

const ACTION_ICONS: Record<string, string> = {
  werewolf_kill: '🐺',
  seer_check: '🔮',
  witch_save: '💊',
  witch_poison: '☠️',
  hunter_shoot: '🏹',
  guard_protect: '🛡️',
  vote: '🗳️',
  speech: '🗣️',
  death: '💀',
}

const ACTION_LABELS: Record<string, string> = {
  werewolf_kill: '狼人袭击',
  seer_check: '预言家查验',
  witch_save: '女巫救人',
  witch_poison: '女巫毒杀',
  hunter_shoot: '猎人开枪',
  guard_protect: '守卫守护',
  vote: '投票',
  speech: '发言',
  death: '死亡',
}

export default function ActionLog({ actions }: ActionLogProps) {
  const scrollRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [actions.length])

  if (actions.length === 0) {
    return (
      <div className="text-sm text-gray-500 py-4 text-center">
        暂无行动记录
      </div>
    )
  }

  return (
    <div className="space-y-2">
      <h4 className="text-sm font-semibold text-gray-300 flex items-center gap-2">
        📋 行动日志
        <span className="text-[10px] text-gray-500 font-normal">({actions.length})</span>
      </h4>

      <div
        ref={scrollRef}
        className="max-h-64 overflow-y-auto space-y-1 pr-1 scrollbar-thin"
      >
        {actions.map((action, index) => {
          const icon = ACTION_ICONS[action.action_type] ?? '⚡'
          const label = ACTION_LABELS[action.action_type] ?? action.action_type

          return (
            <div
              key={index}
              className="flex items-start gap-2 text-xs py-1.5 px-2 rounded bg-werewolf-mid/30 hover:bg-werewolf-mid/50 transition"
            >
              <span className="text-sm mt-0.5 flex-shrink-0">{icon}</span>
              <div className="flex-1 min-w-0">
                <div className="text-gray-300">
                  <span className="font-medium">{label}</span>
                  {action.actor_name && (
                    <span className="text-gray-400">
                      {' '}— {action.actor_seat}号 {action.actor_name}
                    </span>
                  )}
                  {action.target_name && (
                    <span className="text-gray-400">
                      {' → '}{action.target_seat}号 {action.target_name}
                    </span>
                  )}
                </div>
                {action.result && (
                  <div className="text-gray-500 mt-0.5">结果：{action.result}</div>
                )}
              </div>
              <div className="text-[10px] text-gray-600 flex-shrink-0">
                R{action.round}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
