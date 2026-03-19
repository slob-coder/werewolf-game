import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Header from './components/common/Header'
import ProtectedRoute from './components/common/ProtectedRoute'
import HomePage from './pages/HomePage'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import RoomPage from './pages/RoomPage'
import GamePage from './pages/GamePage'
import ReplayPage from './pages/ReplayPage'
import AgentsPage from './pages/AgentsPage'

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-werewolf-dark">
        <Header />
        <main>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/rooms/:id" element={<RoomPage />} />
            <Route
              path="/games/:id"
              element={
                <ProtectedRoute>
                  <GamePage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/games/:id/replay"
              element={
                <ProtectedRoute>
                  <ReplayPage />
                </ProtectedRoute>
              }
            />
            <Route path="/agents" element={<AgentsPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}

export default App
