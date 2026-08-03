import { Navigate, useLocation } from 'react-router'

import styles from './RequireAuth.module.css'
import { useAuth } from './context'

/**
 * ログインが必要な画面の囲い。
 *
 * ★ `loading` を `anonymous` と一緒に扱わないこと。access はメモリにしか
 *   無いので、リロード直後は必ず「まだ分からない」状態を通る。ここで弾くと
 *   **ログイン済みなのに F5 のたびにログイン画面へ飛ばされる**
 *   （docs/06-auth.md）。
 */
export function RequireAuth({ children }: { children: React.ReactNode }) {
  const { status } = useAuth()
  const location = useLocation()

  if (status === 'loading') {
    return <p className={styles.gate}>読み込み中…</p>
  }

  if (status === 'anonymous') {
    // ログイン後にここへ戻す。AuthPage が state.from を見る。
    return (
      <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />
    )
  }

  return <>{children}</>
}
