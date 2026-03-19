interface NightOverlayProps {
  isNight: boolean
  phase?: string
}

const NIGHT_MESSAGES: Record<string, string> = {
  night_start: '天黑了，请闭眼...',
  night_werewolf: '🐺 狼人请睁眼，选择你们的猎物...',
  night_seer: '🔮 预言家请睁眼，选择查验对象...',
  night_witch: '🧙‍♀️ 女巫请睁眼...',
  night_hunter: '🏹 猎人请准备...',
  night_end: '🌅 天亮了...',
}

export default function NightOverlay({ isNight, phase }: NightOverlayProps) {
  if (!isNight) return null

  const message = phase ? NIGHT_MESSAGES[phase] ?? '夜晚进行中...' : '夜晚进行中...'

  return (
    <div className="absolute inset-0 z-20 pointer-events-none overflow-hidden">
      {/* Dark overlay */}
      <div className="absolute inset-0 bg-gradient-to-b from-indigo-950/40 via-blue-950/30 to-indigo-950/40" />

      {/* Stars */}
      <div className="absolute inset-0">
        {Array.from({ length: 20 }).map((_, i) => (
          <div
            key={i}
            className="absolute w-1 h-1 bg-white rounded-full animate-pulse"
            style={{
              left: `${(i * 37 + 13) % 100}%`,
              top: `${(i * 23 + 7) % 100}%`,
              animationDelay: `${i * 0.2}s`,
              opacity: 0.3 + (i % 5) * 0.15,
            }}
          />
        ))}
      </div>

      {/* Moon */}
      <div className="absolute top-4 right-8 text-4xl opacity-60 animate-float">
        🌙
      </div>

      {/* Phase message */}
      <div className="absolute bottom-8 left-1/2 -translate-x-1/2 text-center">
        <div className="text-sm text-indigo-200/80 font-medium tracking-wider animate-pulse">
          {message}
        </div>
      </div>
    </div>
  )
}
