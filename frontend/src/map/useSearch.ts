import { useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'

import { searchLibraries } from '../api/libraries'
import type { SmokingStatus } from '../types/api'

/** 検索結果の表示上限。地図に載せるわけではないので一覧の 200 より大幅に絞る。 */
export const SEARCH_LIMIT = 20

/**
 * 入力が落ち着くまで待つ。
 *
 * ★ 日本語入力では変換の途中でも `onChange` が飛ぶ（「し」「しん」「しんじゅく」…）。
 *   1 打鍵ごとに queryKey が変わると、そのぶんリクエストが出る。
 */
function useDebounced<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value)

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delayMs)
    return () => clearTimeout(timer)
  }, [value, delayMs])

  return debounced
}

/**
 * テキスト検索。
 *
 * **地図のピンは絞り込まない。** これは「探して飛ぶ」ための導線で、
 * 表示中のピンを減らすフィルタではない（それは喫煙区分のほうの役割）。
 */
export function useSearch(input: string, smoking: SmokingStatus[]) {
  const q = useDebounced(input.trim(), 250)

  const query = useQuery({
    queryKey: ['search', q, smoking],
    queryFn: () => searchLibraries({ q, smoking, limit: SEARCH_LIMIT }),
    enabled: q.length > 0,
    staleTime: 60_000,
  })

  // q は「実際に投げた文字列」。入力中の文字で「〜は見つかりません」と
  // 出すと、打っている途中に一瞬 0 件が見えてしまう。
  return { ...query, q }
}
