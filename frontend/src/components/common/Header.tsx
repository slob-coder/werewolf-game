import { Link, useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'

export default function Header() {
  const { isAuthenticated, username, logout } = useAuthStore()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <header className="bg-werewolf-mid border-b border-gray-700 px-6 py-4">
      <nav className="container mx-auto flex items-center justify-between">
        <Link to="/" className="text-xl font-bold text-werewolf-accent flex items-center gap-2">
          🐺 Werewolf Arena
        </Link>
        <div className="flex items-center gap-6 text-gray-300">
          <Link to="/" className="hover:text-white transition">房间</Link>
          <Link to="/agents" className="hover:text-white transition">Agents</Link>
          {isAuthenticated ? (
            <div className="flex items-center gap-4">
              <span className="text-sm text-gray-400">
                👤 {username}
              </span>
              <button
                onClick={handleLogout}
                className="text-sm hover:text-werewolf-accent transition"
              >
                退出
              </button>
            </div>
          ) : (
            <Link to="/login" className="hover:text-white transition">登录</Link>
          )}
        </div>
      </nav>
    </header>
  )
}
