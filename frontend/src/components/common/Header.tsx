export default function Header() {
  return (
    <header className="bg-werewolf-mid border-b border-gray-700 px-6 py-4">
      <nav className="container mx-auto flex items-center justify-between">
        <a href="/" className="text-xl font-bold text-werewolf-accent">
          🐺 Werewolf Arena
        </a>
        <div className="flex gap-6 text-gray-300">
          <a href="/" className="hover:text-white transition">房间</a>
          <a href="/leaderboard" className="hover:text-white transition">排行榜</a>
          <a href="/docs" className="hover:text-white transition">文档</a>
        </div>
      </nav>
    </header>
  )
}
