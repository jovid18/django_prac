import { Navigate, Route, Routes } from 'react-router'

import { AuthPage } from './auth/AuthPage'
import { MapPage } from './map/MapPage'

/**
 * ルーティング。
 *
 * ⚠ `/login` をアドレスバーに直接打って開けるのは、Render の Static Site 側に
 *   `/*` → `/index.html` の rewrite を入れてあるから（render.yaml）。
 *   これが無いと SPA のパスは 404 になる。動作確認シナリオの 11 番目がこれ。
 */
function App() {
  return (
    <Routes>
      <Route path="/" element={<MapPage />} />
      <Route path="/login" element={<AuthPage mode="login" />} />
      <Route path="/register" element={<AuthPage mode="register" />} />
      {/* 未知のパスは地図へ。404 画面は今回作らない。 */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default App
