interface TimelineControlProps {
  currentIndex: number
  totalEvents: number
  isPlaying: boolean
  speed: number
  onTogglePlay: () => void
  onSeek: (index: number) => void
  onSpeedChange: (speed: number) => void
}

const SPEED_OPTIONS = [0.5, 1, 2, 4, 8]

export default function TimelineControl({
  currentIndex,
  totalEvents,
  isPlaying,
  speed,
  onTogglePlay,
  onSeek,
  onSpeedChange,
}: TimelineControlProps) {
  const progress = totalEvents > 0 ? (currentIndex / (totalEvents - 1)) * 100 : 0

  return (
    <div className="bg-werewolf-mid border-t border-gray-700 px-4 py-3">
      <div className="flex items-center gap-4">
        {/* Play/Pause button */}
        <button
          onClick={onTogglePlay}
          className="w-10 h-10 flex items-center justify-center rounded-full bg-werewolf-accent hover:bg-red-600 transition text-white"
          title={isPlaying ? '暂停' : '播放'}
        >
          {isPlaying ? '⏸️' : '▶️'}
        </button>

        {/* Timeline slider */}
        <div className="flex-1 relative">
          <input
            type="range"
            min={0}
            max={Math.max(0, totalEvents - 1)}
            value={currentIndex}
            onChange={(e) => onSeek(Number(e.target.value))}
            className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer
              [&::-webkit-slider-thumb]:appearance-none
              [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4
              [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-werewolf-accent
              [&::-webkit-slider-thumb]:cursor-pointer [&::-webkit-slider-thumb]:shadow-md"
            style={{
              background: `linear-gradient(to right, #e94560 0%, #e94560 ${progress}%, #374151 ${progress}%, #374151 100%)`,
            }}
          />
          <div className="flex justify-between text-[10px] text-gray-500 mt-1">
            <span>{currentIndex + 1}</span>
            <span>{totalEvents} 事件</span>
          </div>
        </div>

        {/* Speed control */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500">速度:</span>
          <div className="flex gap-1">
            {SPEED_OPTIONS.map((s) => (
              <button
                key={s}
                onClick={() => onSpeedChange(s)}
                className={`
                  text-xs px-2 py-1 rounded transition
                  ${speed === s
                    ? 'bg-werewolf-accent text-white'
                    : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
                  }
                `}
              >
                {s}x
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
