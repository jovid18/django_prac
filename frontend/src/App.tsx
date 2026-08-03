import { useEffect, useState } from 'react'
import { env } from './env'

type Health = { status: string; debug: boolean }

type State =
  | { kind: 'loading' }
  | { kind: 'ok'; data: Health; ms: number }
  | { kind: 'error'; message: string }

/**
 * Day 1 の到達点を確認するためだけの画面。
 * 「フロントから API を呼べている」ことが見えれば十分で、
 * 地図もログインも Day 2 以降に置き換える。
 */
function App() {
  const [state, setState] = useState<State>({ kind: 'loading' })

  useEffect(() => {
    const started = performance.now()
    // Render の無料 Web Service はスリープから復帰するのに時間がかかるので、
    // タイムアウトを長めに取る（docs/08-deploy-render.md）。
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), 60_000)

    fetch(`${env.apiBaseUrl}/api/health/`, { signal: controller.signal })
      .then(async (res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const data = (await res.json()) as Health
        setState({ kind: 'ok', data, ms: Math.round(performance.now() - started) })
      })
      .catch((e: unknown) => {
        const message = e instanceof Error ? e.message : String(e)
        setState({ kind: 'error', message })
      })
      .finally(() => clearTimeout(timer))

    return () => clearTimeout(timer)
  }, [])

  return (
    <main>
      <h1>django_prac</h1>
      <p className="sub">東京都の図書館マップ — Day 1 疎通確認</p>

      <dl>
        <dt>API base</dt>
        <dd>
          <code>{env.apiBaseUrl || '(相対パス / Vite proxy)'}</code>
        </dd>

        <dt>Google client ID</dt>
        <dd>
          <code>{env.googleClientId ? '設定済み' : '未設定'}</code>
        </dd>

        <dt>GET /api/health/</dt>
        <dd>
          {state.kind === 'loading' && <span>接続中… (サーバー起動待ちの場合があります)</span>}
          {state.kind === 'ok' && (
            <span className="ok">
              200 · status={state.data.status} · debug={String(state.data.debug)} · {state.ms}ms
            </span>
          )}
          {state.kind === 'error' && <span className="ng">失敗: {state.message}</span>}
        </dd>
      </dl>
    </main>
  )
}

export default App
