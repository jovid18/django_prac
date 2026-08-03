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

export function useGeolocation() {
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
