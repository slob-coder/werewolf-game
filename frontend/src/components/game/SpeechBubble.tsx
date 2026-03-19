import type { SpeechEntry } from '@/types/game'

interface SpeechBubbleProps {
  speech: SpeechEntry
  showCoT?: boolean
}

export default function SpeechBubble({ speech, showCoT = false }: SpeechBubbleProps) {
  return (
    <div className="flex gap-3 mb-3 animate-fade-in">
      {/* Avatar */}
      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-werewolf-light flex items-center justify-center text-xs font-bold">
        {speech.seat}
      </div>

      {/* Bubble */}
      <div className="flex-1 min-w-0">
        <div className="flex items-baseline gap-2 mb-1">
          <span className="text-sm font-semibold text-gray-200">{speech.name}</span>
          <span className="text-[10px] text-gray-500">
            第{speech.round}轮
          </span>
        </div>
        <div className="bg-werewolf-mid rounded-lg rounded-tl-none p-3 text-sm text-gray-200 leading-relaxed">
          {speech.content}
        </div>

        {/* Chain of thought (god view) */}
        {showCoT && speech.chain_of_thought && (
          <details className="mt-1">
            <summary className="text-[10px] text-purple-400 cursor-pointer hover:text-purple-300">
              🧠 查看推理链
            </summary>
            <div className="mt-1 p-2 bg-purple-950/30 rounded text-xs text-purple-300 leading-relaxed border border-purple-800/30">
              {speech.chain_of_thought}
            </div>
          </details>
        )}
      </div>
    </div>
  )
}
