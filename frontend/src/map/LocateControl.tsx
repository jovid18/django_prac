import { AdvancedMarker, useMap } from '@vis.gl/react-google-maps'
import { useEffect } from 'react'

import styles from './LocateControl.module.css'
import { useGeolocation } from './useGeolocation'

/**
 * 現在地ボタン。
 *
 * 起動と同時に権限を求めない。地図が見えている状態で押させるほうが許可率が高く、
 * **拒否されても地図と検索は全部動く**（docs/07-frontend.md）。
 */
export function LocateControl() {
  const map = useMap()
  const { state, request } = useGeolocation()

  useEffect(() => {
    if (state.status !== 'granted' || !map) return
    map.panTo({ lat: state.lat, lng: state.lng })
    map.setZoom(14)
  }, [state, map])

  const message =
    state.status === 'denied'
      ? '位置情報が拒否されています。ブラウザの設定から許可してください。'
      : state.status === 'unavailable'
        ? '現在地を取得できませんでした。'
        : null

  return (
    <>
      <div className={styles.wrap}>
        <button
          type="button"
          className={styles.button}
          onClick={request}
          disabled={state.status === 'loading'}
        >
          <LocateIcon />
          {state.status === 'loading' ? '取得中…' : '現在地'}
        </button>
        {message && <p className={styles.message}>{message}</p>}
      </div>

      {/* 十字の照準アイコン。文字だけより「現在地」だと分かりやすい */}
      {state.status === 'granted' && (
        <AdvancedMarker position={{ lat: state.lat, lng: state.lng }} title="現在地" zIndex={3}>
          <div className={styles.here} aria-label="現在地" />
        </AdvancedMarker>
      )}
    </>
  )
}

function LocateIcon() {
  return (
    <svg
      className={styles.icon}
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      aria-hidden
    >
      <circle cx="12" cy="12" r="3.5" fill="currentColor" stroke="none" />
      <circle cx="12" cy="12" r="7.5" />
      <path d="M12 1.5v3M12 19.5v3M1.5 12h3M19.5 12h3" strokeLinecap="round" />
    </svg>
  )
}
