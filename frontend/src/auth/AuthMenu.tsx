import { Link, useLocation } from 'react-router'

import styles from './AuthMenu.module.css'
import { useAuth } from './context'

/**
 * ヘッダー右端のログイン状態表示。
 *
 * `loading` の間はボタンを出さない。出してしまうと、リロードのたびに
 * 「ログイン」が一瞬見えてからユーザー名に切り替わるチラつきになる。
 */
export function AuthMenu() {
  const { status, user, logout } = useAuth()
  const location = useLocation()

  if (status === 'loading') {
    return <span className={styles.placeholder} aria-hidden />
  }

  if (status === 'anonymous') {
    // ログイン後に今いる画面へ戻すため、現在地を state で渡す。
    const from = location.pathname + location.search
    return (
      <nav className={styles.wrap}>
        <Link className={styles.link} to="/login" state={{ from }}>
          ログイン
        </Link>
        <Link className={styles.primary} to="/register" state={{ from }}>
          登録
        </Link>
      </nav>
    )
  }

  return (
    <div className={styles.wrap}>
      <span className={styles.who} title={user?.email}>
        {user?.display_name || user?.email}
      </span>
      <button className={styles.link} type="button" onClick={() => void logout()}>
        ログアウト
      </button>
    </div>
  )
}
