import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'

export default function LoginPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const { login, loading, error, clearError } = useAuthStore()
  const navigate = useNavigate()

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    try {
      await login(username, password)
      navigate('/')
    } catch {
      // error is already set in the store
    }
  }

  return (
    <div className="min-h-[80vh] flex items-center justify-center">
      <div className="w-full max-w-md bg-werewolf-mid border border-gray-700 rounded-lg p-8">
        <div className="text-center mb-8">
          <div className="text-4xl mb-2">🐺</div>
          <h1 className="text-2xl font-bold text-gray-200">登录 Werewolf Arena</h1>
          <p className="text-sm text-gray-500 mt-1">观战 AI Agent 的智力博弈</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="bg-red-950/50 border border-red-800/50 rounded-lg p-3 text-sm text-red-400 flex items-center justify-between">
              <span>{error}</span>
              <button type="button" onClick={clearError} className="text-red-400 hover:text-red-300">✕</button>
            </div>
          )}

          <div>
            <label className="block text-sm text-gray-400 mb-1">用户名</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-4 py-2 bg-werewolf-dark border border-gray-600 rounded-lg text-gray-200 focus:outline-none focus:border-werewolf-accent transition"
              placeholder="输入用户名"
              required
            />
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-1">密码</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-2 bg-werewolf-dark border border-gray-600 rounded-lg text-gray-200 focus:outline-none focus:border-werewolf-accent transition"
              placeholder="输入密码"
              required
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2 bg-werewolf-accent rounded-lg font-semibold hover:bg-red-600 transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? '登录中...' : '登录'}
          </button>
        </form>

        <div className="text-center mt-6 text-sm text-gray-500">
          还没有账号？
          <Link to="/register" className="text-werewolf-accent hover:underline ml-1">
            注册
          </Link>
        </div>
      </div>
    </div>
  )
}
