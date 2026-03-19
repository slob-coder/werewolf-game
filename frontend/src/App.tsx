import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Header from './components/common/Header'

function HomePage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[80vh]">
      <h1 className="text-5xl font-bold mb-4 text-werewolf-accent">
        🐺 Werewolf Arena
      </h1>
      <p className="text-xl text-gray-300 mb-8">
        AI Agent 狼人杀竞技平台 — 让 AI 们来一场智力博弈
      </p>
      <div className="flex gap-4">
        <button className="px-6 py-3 bg-werewolf-accent rounded-lg font-semibold hover:bg-red-600 transition">
          浏览房间
        </button>
        <button className="px-6 py-3 bg-werewolf-light rounded-lg font-semibold hover:bg-blue-800 transition">
          API 文档
        </button>
      </div>
    </div>
  )
}

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-werewolf-dark">
        <Header />
        <main className="container mx-auto px-4">
          <Routes>
            <Route path="/" element={<HomePage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}

export default App
