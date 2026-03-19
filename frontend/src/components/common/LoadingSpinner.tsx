interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg'
  text?: string
}

export default function LoadingSpinner({ size = 'md', text }: LoadingSpinnerProps) {
  const sizeClass = {
    sm: 'w-5 h-5',
    md: 'w-8 h-8',
    lg: 'w-12 h-12',
  }[size]

  return (
    <div className="flex flex-col items-center justify-center gap-3">
      <div
        className={`${sizeClass} border-2 border-gray-600 border-t-werewolf-accent rounded-full animate-spin`}
      />
      {text && <p className="text-sm text-gray-400">{text}</p>}
    </div>
  )
}
