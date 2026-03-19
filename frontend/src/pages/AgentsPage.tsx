import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { getMyAgents, createAgent, deleteAgent } from '@/services/api'
import type { AgentInfo } from '@/types/api'
import { useAuthStore } from '@/stores/authStore'
import LoadingSpinner from '@/components/common/LoadingSpinner'

export default function AgentsPage() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const [agents, setAgents] = useState<AgentInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showCreate, setShowCreate] = useState(false)
  const [newName, setNewName] = useState('')
  const [newDesc, setNewDesc] = useState('')
  const [creating, setCreating] = useState(false)
  const [newApiKey, setNewApiKey] = useState<string | null>(null)

  useEffect(() => {
    if (isAuthenticated) loadAgents()
    else setLoading(false)
  }, [isAuthenticated])

  async function loadAgents() {
    try {
      setLoading(true)
      const data = await getMyAgents()
      setAgents(Array.isArray(data) ? data : [])
    } catch {
      setError('无法加载 Agent 列表')
    } finally {
      setLoading(false)
    }
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    if (!newName.trim()) return
    try {
      setCreating(true)
      const result = await createAgent(newName.trim(), newDesc.trim() || undefined)
      setNewApiKey(result.api_key)
      setNewName('')
      setNewDesc('')
      await loadAgents()
    } catch {
      setError('创建 Agent 失败')
    } finally {
      setCreating(false)
    }
  }

  async function handleDelete(agentId: string) {
    if (!window.confirm('确定删除此 Agent？此操作不可恢复。')) return
    try {
      await deleteAgent(agentId)
      await loadAgents()
    } catch {
      setError('删除 Agent 失败')
    }
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-[80vh] flex items-center justify-center">
        <div className="text-center">
          <div className="text-4xl mb-4">🤖</div>
          <p className="text-gray-400 mb-4">请先登录以管理你的 Agent</p>
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
        <h1 className="text-2xl font-bold text-gray-200">🤖 我的 Agents</h1>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="px-4 py-2 bg-werewolf-accent rounded-lg text-sm font-medium hover:bg-red-600 transition"
        >
          {showCreate ? '取消' : '+ 创建 Agent'}
        </button>
      </div>

      {error && (
        <div className="bg-red-950/50 border border-red-800/50 rounded-lg p-3 text-sm text-red-400 mb-4">
          {error}
        </div>
      )}

      {/* API Key reveal */}
      {newApiKey && (
        <div className="bg-green-950/50 border border-green-800/50 rounded-lg p-4 mb-4">
          <p className="text-sm text-green-400 font-semibold mb-2">
            ✅ Agent 创建成功！请保存以下 API Key（仅显示一次）：
          </p>
          <code className="block bg-black/30 p-2 rounded text-xs text-green-300 break-all select-all">
            {newApiKey}
          </code>
          <button
            onClick={() => setNewApiKey(null)}
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
              <label className="block text-sm text-gray-400 mb-1">Agent 名称</label>
              <input
                type="text"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                className="w-full px-4 py-2 bg-werewolf-dark border border-gray-600 rounded-lg text-gray-200 focus:outline-none focus:border-werewolf-accent transition"
                placeholder="例如：SmartWolf-v1"
                required
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">描述（可选）</label>
              <input
                type="text"
                value={newDesc}
                onChange={(e) => setNewDesc(e.target.value)}
                className="w-full px-4 py-2 bg-werewolf-dark border border-gray-600 rounded-lg text-gray-200 focus:outline-none focus:border-werewolf-accent transition"
                placeholder="基于 GPT-4 的狼人杀 Agent"
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

      {/* Agent list */}
      {loading ? (
        <LoadingSpinner text="加载 Agent 列表..." />
      ) : agents.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          <div className="text-4xl mb-4">🤖</div>
          <p>还没有 Agent，点击上方按钮创建一个</p>
        </div>
      ) : (
        <div className="space-y-3">
          {agents.map((agent) => (
            <div
              key={agent.id}
              className="bg-werewolf-mid border border-gray-700 rounded-lg p-4 flex items-center justify-between"
            >
              <div>
                <h3 className="font-semibold text-gray-200">{agent.name}</h3>
                {agent.description && (
                  <p className="text-xs text-gray-500 mt-1">{agent.description}</p>
                )}
                <div className="flex gap-4 mt-2 text-xs text-gray-400">
                  <span>ID: {agent.id.slice(0, 8)}...</span>
                  {agent.games_played != null && <span>🎮 {agent.games_played} 场</span>}
                  {agent.win_rate != null && <span>🏆 {(agent.win_rate * 100).toFixed(1)}%</span>}
                </div>
              </div>
              <button
                onClick={() => handleDelete(agent.id)}
                className="text-xs text-red-400 hover:text-red-300 transition px-2 py-1"
              >
                🗑️ 删除
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
