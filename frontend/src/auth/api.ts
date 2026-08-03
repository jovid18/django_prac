import { apiGet, apiPost, setAccessToken } from '../api/client'

/**
 * `/api/auth/*` が返すユーザー。
 * register / login / google / me の 4 つで同じ形（backend の UserSerializer）。
 */
export type AuthUser = {
  id: number
  email: string
  display_name: string
  /** ID/PW を持っているか。Google だけのアカウントは false。 */
  has_password: boolean
  /** 連携済みプロバイダ（`["google"]`）。 */
  providers: string[]
  date_joined: string
}

/** ★ refresh は本文に入らない。HttpOnly Cookie で返る。 */
type AuthResponse = { user: AuthUser; access: string; created?: boolean }

/** ログイン系のレスポンスを受けて、アクセストークンをメモリに載せる。 */
function accept(result: AuthResponse): AuthUser {
  setAccessToken(result.access)
  return result.user
}

// ログイン系は 401 で refresh を試さない（skipRefresh）。
// 「パスワードが違う」の 401 で refresh に走るのは無意味で、
// 進行中のログイン状態を壊しかねない。

export async function register(input: {
  email: string
  password: string
  display_name?: string
}): Promise<AuthUser> {
  return accept(await apiPost<AuthResponse>('/api/auth/register/', input, { skipRefresh: true }))
}

export async function login(input: { email: string; password: string }): Promise<AuthUser> {
  return accept(await apiPost<AuthResponse>('/api/auth/login/', input, { skipRefresh: true }))
}

export async function loginWithGoogle(idToken: string): Promise<AuthUser> {
  return accept(
    await apiPost<AuthResponse>(
      '/api/auth/google/',
      { id_token: idToken },
      { skipRefresh: true },
    ),
  )
}

export function fetchMe(): Promise<AuthUser> {
  return apiGet<AuthUser>('/api/auth/me/')
}

export async function logout(): Promise<void> {
  await apiPost<void>('/api/auth/logout/')
  setAccessToken(null)
}
