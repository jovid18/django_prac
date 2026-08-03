import { env } from '../env'

export class ApiError extends Error {
  // ⚠ コンストラクタの引数プロパティ（`constructor(readonly status: number)`）は
  //    使えない。tsconfig の `erasableSyntaxOnly` が TS 固有構文を禁じている。
  status: number
  /** DRF のエラー本文（`{detail}` か `{field: [...]}`）。フォームの表示に使う。 */
  body: unknown

  constructor(status: number, message: string, body: unknown = null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.body = body
  }
}

type Params = Record<string, string | number | undefined>

type RequestOptions = {
  method?: 'GET' | 'POST' | 'DELETE'
  params?: Params
  /** JSON にして送る本文。**オブジェクトのまま持つ**（リトライで再送するため）。 */
  json?: unknown
  /** 401 のときに refresh を試さない。refresh 自身とログイン系で使う。 */
  skipRefresh?: boolean
}

// --- アクセストークン -------------------------------------------------------
//
// ★ localStorage に置かない。同一オリジンの JS から全部読めるので、依存
//   ライブラリ 1 つが汚染されただけで持ち出される。メモリなのでリロードで
//   消えるが、起動時に refresh を 1 回叩けば復帰できる（docs/06-auth.md）。

let accessToken: string | null = null

export function setAccessToken(token: string | null) {
  accessToken = token
}

/** refresh も失敗した = ログイン状態が切れた。AuthContext がここに繋ぐ。 */
let onSessionExpired: (() => void) | null = null

export function setSessionExpiredHandler(handler: (() => void) | null) {
  onSessionExpired = handler
}

// --- リクエスト -------------------------------------------------------------

function buildUrl(path: string, params: Params = {}) {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === '') continue
    search.set(key, String(value))
  }
  const qs = search.toString()
  return `${env.apiBaseUrl}${path}${qs ? `?${qs}` : ''}`
}

function send(path: string, options: RequestOptions) {
  const headers: Record<string, string> = { Accept: 'application/json' }
  if (options.json !== undefined) headers['Content-Type'] = 'application/json'
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`

  return fetch(buildUrl(path, options.params), {
    method: options.method ?? 'GET',
    headers,
    // ★ リフレッシュ Cookie を送るために必須。本番はクロスオリジンなので、
    //   これが無いと Cookie が付かず「毎回ログアウトされる」になる。
    credentials: 'include',
    body: options.json === undefined ? undefined : JSON.stringify(options.json),
  })
}

/**
 * 進行中の refresh。
 *
 * ★ 同時に複数のリクエストが 401 になっても refresh は 1 回にまとめる。
 *   ROTATE_REFRESH_TOKENS を有効にしてあるので、2 本同時に投げると
 *   後から届いた方が「ブラックリスト済みの Cookie」を使うことになり、
 *   正しいトークンまで無効化される（docs/06-auth.md）。
 *
 *   React の StrictMode は effect を 2 回走らせるので、これが無いと
 *   **開発中は必ず**この競合を踏む。
 */
let inFlightRefresh: Promise<boolean> | null = null

export function refreshAccessToken(): Promise<boolean> {
  inFlightRefresh ??= runRefresh().finally(() => {
    inFlightRefresh = null
  })
  return inFlightRefresh
}

async function runRefresh(): Promise<boolean> {
  try {
    // 本文なし。リフレッシュトークンは Cookie で送られる。
    const res = await send('/api/auth/refresh/', { method: 'POST', skipRefresh: true })
    if (!res.ok) return false
    const data = (await res.json()) as { access: string }
    setAccessToken(data.access)
    return true
  } catch {
    // 通信自体が失敗した場合。ログイン画面に飛ばす材料にはしない。
    return false
  }
}

async function parseError(res: Response): Promise<ApiError> {
  let body: unknown = null
  try {
    body = await res.json()
  } catch {
    // 本文が空 or HTML（502 など）
  }
  return new ApiError(res.status, `HTTP ${res.status}`, body)
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  let res = await send(path, options)

  if (res.status === 401 && !options.skipRefresh) {
    const refreshed = await refreshAccessToken()
    if (!refreshed) {
      setAccessToken(null)
      onSessionExpired?.()
      throw await parseError(res)
    }
    // ★ リトライは 1 回だけ。ここでループさせると無限リクエストになる。
    res = await send(path, options)
  }

  if (!res.ok) throw await parseError(res)
  // 204 No Content（logout）。json() を呼ぶと SyntaxError になる。
  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}

export function apiGet<T>(path: string, params: Params = {}): Promise<T> {
  return request<T>(path, { params })
}

export function apiPost<T>(
  path: string,
  json?: unknown,
  options: { skipRefresh?: boolean } = {},
): Promise<T> {
  return request<T>(path, { method: 'POST', json, skipRefresh: options.skipRefresh })
}

/**
 * DRF のエラー本文を 1 行のメッセージにする。
 *
 * `{"detail": "..."}` と `{"email": ["..."], "password": ["..."]}` の
 * 2 形式が来る（docs/05-api.md）。フォームの表示で毎回書き分けたくないので、
 * ここで畳んでしまう。
 */
export function apiErrorMessage(error: unknown, fallback = 'エラーが発生しました。'): string {
  if (!(error instanceof ApiError)) return fallback
  if (error.status === 429) return '試行回数が多すぎます。1 分ほど待ってからやり直してください。'
  if (error.status >= 500) return 'サーバでエラーが発生しました。しばらくしてからやり直してください。'

  const body = error.body
  if (typeof body !== 'object' || body === null) return fallback

  const entries = Object.entries(body as Record<string, unknown>)
  const messages = entries.flatMap(([, value]) =>
    Array.isArray(value) ? value.map(String) : [String(value)],
  )
  return messages.length > 0 ? messages.join(' ') : fallback
}
