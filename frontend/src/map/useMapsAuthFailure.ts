import { useEffect, useState } from 'react'

/**
 * Maps JS の「キーの認証に失敗した」を拾う。
 *
 * ★ これは `APIProvider` のロード状態では検出できない。
 *   `RefererNotAllowedMapError` / `ApiNotActivatedMapError` /
 *   `BillingNotEnabledMapError` はどれも **スクリプトの読み込みには成功した後**に
 *   起きるので、ローディング状態は `LOADED` のまま成功扱いになる。
 *
 *   実際に localhost 以外のオリジンから開いて確認した見え方（docs/07-frontend.md）:
 *   - Google が地図の枠内に**自前のライト配色のエラー画面**を出す（ダークモードに追従しない）
 *   - こちらの UI は何も知らないので、フッターが「152 件表示中」と嘘をつき続ける
 *
 *   `window.gm_authFailure` は Google が用意しているグローバルなコールバックで、
 *   この状況を知る唯一の手段。**関数を代入して待つ**という API なので、
 *   イベントリスナのようには扱えない。
 */

type WithAuthFailure = { gm_authFailure?: () => void }

export function useMapsAuthFailure(): boolean {
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    const target = globalThis as WithAuthFailure
    const previous = target.gm_authFailure
    target.gm_authFailure = () => {
      setFailed(true)
      previous?.()
    }
    return () => {
      target.gm_authFailure = previous
    }
  }, [])

  return failed
}
