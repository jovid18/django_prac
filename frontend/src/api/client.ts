import { env } from '../env'

export class ApiError extends Error {
  // ⚠ コンストラクタの引数プロパティ（`constructor(readonly status: number)`）は
  //    使えない。tsconfig の `erasableSyntaxOnly` が TS 固有構文を禁じている。
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

type Params = Record<string, string | number | undefined>

/**
 * fetch の薄いラッパ。
 *
 * Day 4 で「401 → refresh → 1 回だけリトライ」をここに足す（docs/06-auth.md）。
 * 図書館の閲覧は認証不要なので、今はトークンを持たない。
 */
export async function apiGet<T>(path: string, params: Params = {}): Promise<T> {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === '') continue
    search.set(key, String(value))
  }
  const qs = search.toString()
  const res = await fetch(`${env.apiBaseUrl}${path}${qs ? `?${qs}` : ''}`, {
    headers: { Accept: 'application/json' },
  })

  if (!res.ok) {
    throw new ApiError(res.status, `HTTP ${res.status}`)
  }
  return (await res.json()) as T
}
