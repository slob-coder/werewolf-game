import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { getMyAccessKeys, createAccessKey, revokeAccessKey } from '@/services/api'
import type { AccessKeyInfo } from '@/types/api'
import { useAuthStore } from '@/stores/authStore'
import LoadingSpinner from '@/components/common/LoadingSpinner'

export default function AccessKeysPage() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const [accessKeys, setAccessKeys] = useState<AccessKeyInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showCreate, setShowCreate] = useState(false)
  const [newName, setNewName] = useState('')
  const [creating, setCreating] = useState(false)
  const [newKey, setNewKey] = useState<string | null>(null)

  useEffect(() => {
    if (isAuthenticated) loadAccessKeys()
    else setLoading(false)
  }, [isAuthenticated])

  async function loadAccessKeys() {
    try {
      setLoading(true)
      const data = await getMyAccessKeys()
      setAccessKeys(Array.isArray(data) ? data : [])
    } catch {
      setError('无法加载 Access Key 列表')
    } finally {
      setLoading(false)
    }
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    try {
      setCreating(true)
      const result = await createAccessKey(newName.trim() || undefined)
      setNewKey(result.key)
      setNewName('')
      setShowCreate(false)
      await loadAccessKeys()
    } catch {
      setError('创建 Access Key 失败')
    } finally {
      setCreating(false)
    }
  }

  async function handleRevoke(keyId: string) {
    if (!window.confirm('确定撤销此 Access Key？撤销后使用该 Key 的 CLI 将无法登录。')) return
    try {
      await revokeAccessKey(keyId)
      await loadAccessKeys()
    } catch {
      setError('撤销 Access Key 失败')
    }
  }

  function formatDate(dateStr: string) {
    return new Date(dateStr).toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-[80vh] flex items-center justify-center">
        <div className="text-center">
          <div className="text-4xl mb-4">🔑</div>
          <p className="text-gray-400 mb-4">请先登录以管理你的 Access Keys</p>
          <Link to="/login" className="px-4 py-2 bg-werewolf-accent rounded-lg hover:bg-red-600 transition">
            去登录
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-3xl mx-auto py-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-200">🔑 Access Keys</h1>
          <p className="text-sm text-gray-500 mt-1">用于 CLI 初始化的访问密钥</p>
        </div>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="px-4 py-2 bg-werewolf-accent rounded-lg text-sm font-medium hover:bg-red-600 transition"
        >
          {showCreate ? '取消' : '+ 创建 Key'}
        </button>
      </div>

      {/* Usage hint */}
      <div className="bg-blue-950/30 border border-blue-800/30 rounded-lg p-4 mb-6">
        <p className="text-sm text-blue-300">
          <strong>使用方式：</strong>在 CLI 中运行 <code className="bg-black/30 px-1 rounded">werewolf_cli.py init --access-key &lt;your_key&gt;</code> 进行初始化。
        </p>
      </div>

      {error && (
        <div className="bg-red-950/50 border border-red-800/50 rounded-lg p-3 text-sm text-red-400 mb-4">
          {error}
        </div>
      )}

      {/* New key reveal */}
      {newKey && (
        <div className="bg-green-950/50 border border-green-800/50 rounded-lg p-4 mb-4">
          <p className="text-sm text-green-400 font-semibold mb-2">
            ✅ Access Key 创建成功！请保存以下密钥（仅显示一次）：
          </p>
          <code className="block bg-black/30 p-3 rounded text-sm text-green-300 break-all select-all font-mono">
            {newKey}
          </code>
          <button
            onClick={() => setNewKey(null)}
            className="mt-2 text-xs text-green-400 hover:text-green-300"
          >
            我已保存，关闭
          </button>
        </div>
      )}

      {/* Create form */}
      {showCreate && (
        <form onSubmit={handleCreate} className="bg-werewolf-mid border border-gray-700 rounded-lg p-4 mb-6">
          <div className="space-y-3">
            <div>
              <label className="block text-sm text-gray-400 mb-1">名称（可选）</label>
              <input
                type="text"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                className="w-full px-4 py-2 bg-werewolf-dark border border-gray-600 rounded-lg text-gray-200 focus:outline-none focus:border-werewolf-accent transition"
                placeholder="例如：CLI、CI/CD"
              />
            </div>
            <button
              type="submit"
              disabled={creating}
              className="px-4 py-2 bg-werewolf-accent rounded-lg text-sm hover:bg-red-600 transition disabled:opacity-50"
            >
              {creating ? '创建中...' : '创建'}
            </button>
          </div>
        </form>
      )}

      {/* Key list */}
      {loading ? (
        <LoadingSpinner text="加载 Access Key 列表..." />
      ) : accessKeys.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          <div className="text-4xl mb-4">🔑</div>
          <p>还没有 Access Key，点击上方按钮创建一个</p>
        </div>
      ) : (
        <div className="space-y-3">
          {accessKeys.map((key) => (
            <div
              key={key.id}
              className={`bg-werewolf-mid border border-gray-700 rounded-lg p-4 ${
                !key.is_active ? 'opacity-50' : ''
              }`}
            >
              <div className="flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold text-gray-200">
                      {key.name || '未命名'}
                    </h3>
                    {key.is_active ? (
                      <span className="text-xs bg-green-800/50 text-green-400 px-2 py-0.5 rounded">
                        活跃
                      </span>
                    ) : (
                      <span className="text-xs bg-red-800/50 text-red-400 px-2 py-0.5 rounded">
                        已撤销
                      </span>
                    )}
                  </div>
                  <div className="flex gap-4 mt-2 text-xs text-gray-400">
                    <span>ID: {key.id.slice(0, 8)}...</span>
                    <span>创建: {formatDate(key.created_at)}</span>
                    {key.last_used_at && (
                      <span>最后使用: {formatDate(key.last_used_at)}</span>
                    )}
                  </div>
                </div>
                {key.is_active && (
                  <button
                    onClick={() => handleRevoke(key.id)}
                    className="text-xs text-red-400 hover:text-red-300 transition px-2 py-1"
                  >
                    撤销
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
