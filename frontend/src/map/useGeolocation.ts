import { useCallback, useState } from 'react'

/**
 * 現在地。
 *
 * 状態を 5 つに分けているのは、**「まだ押していない」と「拒否された」で UI を
 * 変える**ため。拒否された後に再度押しても OS / ブラウザが黙って失敗させるので、
 * その場合は「ブラウザの設定から許可してください」と案内する。
 */
export type GeoState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'granted'; lat: number; lng: number }
  | { status: 'denied' }
  /** HTTPS でない / 非対応ブラウザ / タイムアウト */
  | { status: 'unavailable' }

/**
 * 現在地の状態と取得のトリガ。
 *
 * ★ この型を切っているのは、**フックを `MapPage` で 1 回だけ呼んで
 *   結果を配る**ため。現在地ボタン（地図の内側）と「近い順」（地図の外側）の
 *   両方が同じ状態を見る必要があり、それぞれがフックを呼ぶと許可を 2 回求める
 *   ことになる（docs/07-frontend.md）。
 */
export type Geolocation = {
  state: GeoState
  request: () => void
}

export function useGeolocation(): Geolocation {
  const [state, setState] = useState<GeoState>({ status: 'idle' })

  const request = useCallback(() => {
    // navigator.geolocation は HTTPS か localhost でしか使えない
    if (!('geolocation' in navigator)) {
      setState({ status: 'unavailable' })
      return
    }

    setState({ status: 'loading' })
    navigator.geolocation.getCurrentPosition(
      (pos) => setState({ status: 'granted', lat: pos.coords.latitude, lng: pos.coords.longitude }),
      (err) => {
        // PERMISSION_DENIED(1) だけは「拒否」として別扱いにする
        setState({ status: err.code === err.PERMISSION_DENIED ? 'denied' : 'unavailable' })
      },
      // 高精度を要求すると屋内で長時間待たされる
      { enableHighAccuracy: false, timeout: 8000, maximumAge: 60_000 },
    )
  }, [])

  return { state, request }
}
