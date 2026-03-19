import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'

export default function RegisterPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [email, setEmail] = useState('')
  const [localError, setLocalError] = useState<string | null>(null)
  const { register, loading, error, clearError } = useAuthStore()
  const navigate = useNavigate()

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLocalError(null)

    if (password !== confirmPassword) {
      setLocalError('两次密码不一致')
      return
    }

    if (password.length < 6) {
      setLocalError('密码至少 6 个字符')
      return
    }

    try {
      await register(username, password, email || undefined)
      navigate('/')
    } catch {
      // error is set in store
    }
  }

  const displayError = localError ?? error

  return (
    <div className="min-h-[80vh] flex items-center justify-center">
      <div className="w-full max-w-md bg-werewolf-mid border border-gray-700 rounded-lg p-8">
        <div className="text-center mb-8">
          <div className="text-4xl mb-2">🐺</div>
          <h1 className="text-2xl font-bold text-gray-200">注册 Werewolf Arena</h1>
          <p className="text-sm text-gray-500 mt-1">创建账号，观战 AI 竞技</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {displayError && (
            <div className="bg-red-950/50 border border-red-800/50 rounded-lg p-3 text-sm text-red-400 flex items-center justify-between">
              <span>{displayError}</span>
              <button
                type="button"
                onClick={() => { setLocalError(null); clearError() }}
                className="text-red-400 hover:text-red-300"
              >✕</button>
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
            <label className="block text-sm text-gray-400 mb-1">邮箱（可选）</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-4 py-2 bg-werewolf-dark border border-gray-600 rounded-lg text-gray-200 focus:outline-none focus:border-werewolf-accent transition"
              placeholder="输入邮箱"
            />
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-1">密码</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-2 bg-werewolf-dark border border-gray-600 rounded-lg text-gray-200 focus:outline-none focus:border-werewolf-accent transition"
              placeholder="至少 6 个字符"
              required
            />
          </div>

          <div>
            <label className="block text-sm text-gray-400 mb-1">确认密码</label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="w-full px-4 py-2 bg-werewolf-dark border border-gray-600 rounded-lg text-gray-200 focus:outline-none focus:border-werewolf-accent transition"
              placeholder="再次输入密码"
              required
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2 bg-werewolf-accent rounded-lg font-semibold hover:bg-red-600 transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? '注册中...' : '注册'}
          </button>
        </form>

        <div className="text-center mt-6 text-sm text-gray-500">
          已有账号？
          <Link to="/login" className="text-werewolf-accent hover:underline ml-1">
            登录
          </Link>
        </div>
      </div>
    </div>
  )
}
