import { Navigate, Route, Routes } from 'react-router'

import { AuthPage } from './auth/AuthPage'
import { RequireAuth } from './auth/RequireAuth'
import { FavoritesPage } from './favorites/FavoritesPage'
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
      {/* お気に入りだけログインが必要。地図・一覧・詳細は未ログインで見られる。 */}
      <Route
        path="/favorites"
        element={
          <RequireAuth>
            <FavoritesPage />
          </RequireAuth>
        }
      />
      {/* 未知のパスは地図へ。404 画面は今回作らない。 */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default App
