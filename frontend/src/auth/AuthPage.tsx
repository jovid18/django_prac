import { useState } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router'

import { apiErrorMessage } from '../api/client'
import styles from './AuthForm.module.css'
import { GoogleSignInButton } from './GoogleSignInButton'
import { useAuth } from './context'

type Mode = 'login' | 'register'

const TEXT = {
  login: {
    title: 'ログイン',
    submit: 'ログイン',
    switchTo: '/register',
    switchLabel: 'アカウントを作る',
    googleText: 'signin_with',
  },
  register: {
    title: 'アカウント登録',
    submit: '登録する',
    switchTo: '/login',
    switchLabel: 'ログインに戻る',
    googleText: 'signup_with',
  },
} as const

export function AuthPage({ mode }: { mode: Mode }) {
  const auth = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const text = TEXT[mode]
  // ログインを要求されて飛ばされてきた場合は元の場所に戻す。
  const from = (location.state as { from?: string } | null)?.from ?? '/'

  if (auth.status === 'authenticated') return <Navigate to={from} replace />

  async function run(action: () => Promise<void>) {
    setError(null)
    setBusy(true)
    try {
      await action()
      // 成功したら元の画面へ。replace にして「戻る」でログイン画面に戻らせない。
      void navigate(from, { replace: true })
    } catch (err) {
      setError(apiErrorMessage(err, '処理に失敗しました。'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <h1 className={styles.title}>{text.title}</h1>

        <form
          className={styles.form}
          onSubmit={(event) => {
            event.preventDefault()
            void run(() =>
              mode === 'login'
                ? auth.login({ email, password })
                : auth.register({ email, password, display_name: displayName }),
            )
          }}
        >
          {/* ★ `name` / `id` を付けている理由は「関連付け」ではない。
              `<label>` で包んであるのでアクセシビリティ上の関連付けは既にできている。
              付けないと Chrome が `A form field element should have an id or name
              attribute` を出し、**パスワードマネージャの自動入力が効きにくい**
              （Day 4 で見つけた実害。docs/10-roadmap.md）。 */}
          <label className={styles.field} htmlFor="email">
            <span className={styles.label}>メールアドレス</span>
            <input
              id="email"
              name="email"
              className={styles.input}
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              required
            />
          </label>

          {mode === 'register' && (
            <label className={styles.field} htmlFor="display_name">
              <span className={styles.label}>表示名（任意）</span>
              <input
                id="display_name"
                name="display_name"
                className={styles.input}
                type="text"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                maxLength={50}
                autoComplete="nickname"
              />
            </label>
          )}

          <label className={styles.field} htmlFor="password">
            <span className={styles.label}>パスワード</span>
            <input
              id="password"
              name="password"
              className={styles.input}
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              // ★ 登録時は new-password。ここを current-password にすると
              //   ブラウザが「既存のパスワードを入れる欄」と誤解する。
              autoComplete={mode === 'register' ? 'new-password' : 'current-password'}
              required
            />
          </label>

          {mode === 'register' && (
            <p className={styles.hint}>8 文字以上。よくあるパスワードや数字だけは使えません。</p>
          )}

          {error && (
            <p className={styles.error} role="alert">
              {error}
            </p>
          )}

          <button className={styles.submit} type="submit" disabled={busy}>
            {busy ? '送信中…' : text.submit}
          </button>
        </form>

        <div className={styles.divider}>
          <span>または</span>
        </div>

        <GoogleSignInButton
          text={text.googleText}
          onCredential={(idToken) => void run(() => auth.loginWithGoogle(idToken))}
        />

        <nav className={styles.links}>
          <Link to={text.switchTo}>{text.switchLabel}</Link>
          <Link to="/">地図に戻る</Link>
        </nav>
      </div>
    </div>
  )
}
