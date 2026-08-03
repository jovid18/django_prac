import { useEffect, useRef, useState } from 'react'

import { env } from '../env'
import styles from './AuthForm.module.css'

/**
 * Google Identity Services（GSI）のボタン。
 *
 * ★ スクリプトを index.html に置かず、このコンポーネントから読み込む。
 *   地図の `APIProvider` を MapPage に置いたのと同じ理由で、
 *   ログイン画面を開いていないユーザーに外部スクリプトを読ませない
 *   （docs/07-frontend.md）。
 *
 * ★ ID トークン方式なのでリダイレクトもクライアントシークレットも要らない。
 *   ブラウザ上でサインインが完結し、`credential` に ID トークン（JWT）が入る。
 *   サーバはそれを検証するだけ（docs/06-auth.md）。
 */

// ★ `?hl=ja` を付ける。地図の `language="ja"` と同じ理由で、既定は
//   ブラウザの言語に追従するのでボタンのラベルが英語になる（実測）。
//   renderButton の `locale` だけでは効かなかった。
const GSI_SRC = 'https://accounts.google.com/gsi/client?hl=ja'

type GsiButtonOptions = {
  type?: 'standard'
  theme?: 'outline' | 'filled_blue'
  size?: 'large' | 'medium'
  text?: 'signin_with' | 'signup_with' | 'continue_with'
  shape?: 'rectangular' | 'pill'
  locale?: string
  width?: number
}

type GsiId = {
  initialize(config: {
    client_id: string
    callback: (response: { credential: string }) => void
    auto_select?: boolean
    cancel_on_tap_outside?: boolean
  }): void
  renderButton(parent: HTMLElement, options: GsiButtonOptions): void
  disableAutoSelect(): void
}

// ⚠ `declare global { interface Window { google } }` は使わない。
//    @types/google.maps が同名の `google` 名前空間を持っているので、
//    グローバル拡張をぶつけると型が壊れる。ここだけで畳んで参照する。
function gsi(): GsiId | undefined {
  return (globalThis as { google?: { accounts?: { id?: GsiId } } }).google?.accounts?.id
}

let scriptPromise: Promise<void> | null = null

function loadGsiScript(): Promise<void> {
  // 読み込みは 1 回だけ。ログイン画面と登録画面を行き来しても再読込しない。
  scriptPromise ??= new Promise<void>((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>(`script[src="${GSI_SRC}"]`)
    if (existing) {
      resolve()
      return
    }
    const script = document.createElement('script')
    script.src = GSI_SRC
    script.async = true
    script.defer = true
    script.onload = () => resolve()
    script.onerror = () => reject(new Error('GSI script failed to load'))
    document.head.append(script)
  })
  return scriptPromise
}

export function GoogleSignInButton({
  onCredential,
  text = 'continue_with',
}: {
  onCredential: (idToken: string) => void
  text?: GsiButtonOptions['text']
}) {
  const container = useRef<HTMLDivElement>(null)
  const [failed, setFailed] = useState(false)

  // コールバックは GSI に一度渡したら差し替えられないので、最新を ref で見る。
  const callback = useRef(onCredential)
  callback.current = onCredential

  useEffect(() => {
    if (!env.googleClientId) return
    let alive = true

    void loadGsiScript()
      .then(() => {
        const id = gsi()
        if (!alive || !id || !container.current) return
        id.initialize({
          client_id: env.googleClientId,
          callback: (response) => callback.current(response.credential),
          // ワンタップの自動サインインはしない。ユーザーが押したときだけ動かす。
          auto_select: false,
        })
        id.renderButton(container.current, {
          type: 'standard',
          theme: 'outline',
          size: 'large',
          shape: 'rectangular',
          text,
          locale: 'ja',
        })
      })
      .catch(() => {
        if (alive) setFailed(true)
      })

    return () => {
      alive = false
    }
  }, [text])

  if (!env.googleClientId) {
    return (
      <p className={styles.hint}>
        Google ログインは無効です（<code>VITE_GOOGLE_OAUTH_CLIENT_ID</code> が未設定）。
      </p>
    )
  }
  if (failed) {
    return <p className={styles.error}>Google のログインボタンを読み込めませんでした。</p>
  }

  // GSI が iframe を差し込む先。高さを確保しておかないと読み込み時に跳ねる。
  return <div ref={container} className={styles.googleButton} />
}
