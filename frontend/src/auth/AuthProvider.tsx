import { useCallback, useEffect, useMemo, useState } from 'react'

import { refreshAccessToken, setAccessToken, setSessionExpiredHandler } from '../api/client'
import * as authApi from './api'
import type { AuthUser } from './api'
import { AuthContext, type AuthStatus } from './context'

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [status, setStatus] = useState<AuthStatus>('loading')

  // refresh も失敗した = セッションが切れた。client.ts から呼ばれる。
  useEffect(() => {
    setSessionExpiredHandler(() => {
      setUser(null)
      setStatus('anonymous')
    })
    return () => setSessionExpiredHandler(null)
  }, [])

  /**
   * ★ 起動時に refresh を 1 回叩いてログイン状態を復帰させる。
   *
   *   access はメモリにしか無いのでリロードで消える。これをやらないと
   *   「F5 のたびにログアウトされる」になる（docs/06-auth.md）。
   *
   *   401 は異常ではない。**未ログインの初回アクセスも 401 で来る**ので、
   *   その場合は黙って anonymous にする。
   *
   *   StrictMode で effect が 2 回走るが、`refreshAccessToken` が
   *   単一化してあるので refresh の同時実行にはならない（client.ts）。
   */
  useEffect(() => {
    let alive = true

    void (async () => {
      const refreshed = await refreshAccessToken()
      if (!alive) return
      if (!refreshed) {
        setStatus('anonymous')
        return
      }
      try {
        const me = await authApi.fetchMe()
        if (!alive) return
        setUser(me)
        setStatus('authenticated')
      } catch {
        if (!alive) return
        setAccessToken(null)
        setStatus('anonymous')
      }
    })()

    return () => {
      alive = false
    }
  }, [])

  const succeed = useCallback((me: AuthUser) => {
    setUser(me)
    setStatus('authenticated')
  }, [])

  const value = useMemo(
    () => ({
      status,
      user,
      login: async (input: { email: string; password: string }) =>
        succeed(await authApi.login(input)),
      register: async (input: { email: string; password: string; display_name?: string }) =>
        succeed(await authApi.register(input)),
      loginWithGoogle: async (idToken: string) =>
        succeed(await authApi.loginWithGoogle(idToken)),
      logout: async () => {
        try {
          await authApi.logout()
        } finally {
          // 通信が失敗してもクライアント側は必ずログアウト状態にする。
          // 「押したのにログアウトできない」より、手元を切ってしまうほうが安全。
          setAccessToken(null)
          setUser(null)
          setStatus('anonymous')
        }
      },
    }),
    [status, user, succeed],
  )

  return <AuthContext value={value}>{children}</AuthContext>
}
