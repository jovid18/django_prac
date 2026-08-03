import { createContext, use } from 'react'

import type { AuthUser } from './api'

/**
 * 認証状態は 3 つ。
 *
 * ★ `loading` を分けているのが要点。access はメモリなのでリロードで消え、
 *   起動時の refresh が終わるまで「ログイン済みかどうか分からない」状態がある。
 *   ここを `anonymous` と一緒にしてしまうと、リロードのたびに一瞬
 *   「ログイン」ボタンが出て、直後にユーザー名に切り替わるチラつきになる。
 */
export type AuthStatus = 'loading' | 'authenticated' | 'anonymous'

export type AuthContextValue = {
  status: AuthStatus
  user: AuthUser | null
  login: (input: { email: string; password: string }) => Promise<void>
  register: (input: { email: string; password: string; display_name?: string }) => Promise<void>
  loginWithGoogle: (idToken: string) => Promise<void>
  logout: () => Promise<void>
}

export const AuthContext = createContext<AuthContextValue | null>(null)

export function useAuth(): AuthContextValue {
  // React 19 の `use()`。useContext と同じだが、条件分岐の中でも呼べる。
  const value = use(AuthContext)
  if (!value) throw new Error('useAuth は <AuthProvider> の内側で使う。')
  return value
}
