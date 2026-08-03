import { APIProvider, ControlPosition, MapControl } from '@vis.gl/react-google-maps'
import { useState } from 'react'

import { AuthMenu } from '../auth/AuthMenu'
import { env } from '../env'
import type { LibraryListItem, SmokingStatus } from '../types/api'
import { LibraryMarkers } from './LibraryMarkers'
import { LibraryPanel } from './LibraryPanel'
import { LocateControl } from './LocateControl'
import { MapErrorBoundary } from './MapErrorBoundary'
import styles from './MapPage.module.css'
import { MapPlaceholder, MapView, type MapViewState } from './MapView'
import { SearchBox } from './SearchBox'
import { SmokingFilter } from './SmokingFilter'
import { MIN_FETCH_ZOOM, useLibraries } from './useLibraries'
import { useMapsAuthFailure } from './useMapsAuthFailure'

export function MapPage() {
  const [view, setView] = useState<MapViewState | null>(null)
  const [smoking, setSmoking] = useState<SmokingStatus[]>([])
  const [selected, setSelected] = useState<LibraryListItem | null>(null)
  // 検索結果から panTo するために地図インスタンスを持つ（MapView の
  // MapInstanceReporter が入れる）。地図が無効・失敗しているときは null。
  const [map, setMap] = useState<google.maps.Map | null>(null)
  // キーのリファラー制限違反・請求先無効など。地図は出ないが API は動く。
  const mapAuthFailed = useMapsAuthFailure()

  const { data, isFetching, isError, refetch, zoomTooLow } = useLibraries(view, smoking)
  const items = data?.results ?? []

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.headline}>
          <h1 className={styles.title}>東京都の図書館マップ</h1>
          <AuthMenu />
        </div>
        <p className={styles.note}>
          ※ 喫煙区分は開発練習用の自動生成ダミーで、実際の施設とは関係ありません。
        </p>
      </header>

      <main className={styles.mapArea}>
        <MapErrorBoundary fallback={<MapAuthFailurePlaceholder />}>
          <MapArea onSettled={setView} onMapReady={setMap} authFailed={mapAuthFailed}>
            <LibraryMarkers
              items={items}
              bbox={view?.bbox ?? null}
              zoom={view?.zoom ?? 0}
              selectedId={selected?.id ?? null}
              onSelect={setSelected}
            />
            <MapControl position={ControlPosition.RIGHT_BOTTOM}>
              <LocateControl />
            </MapControl>
          </MapArea>
        </MapErrorBoundary>

        <div className={styles.overlayLeft}>
          <SearchBox smoking={smoking} map={map} onSelect={setSelected} />
          <SmokingFilter value={smoking} onChange={setSmoking} />
        </div>

        <div className={styles.overlayTop}>
          {zoomTooLow && <Toast>地図を拡大してください（この範囲では検索しません）</Toast>}
          {!zoomTooLow && isError && (
            <Toast tone="error">
              データを取得できませんでした。
              <button type="button" className={styles.retry} onClick={() => refetch()}>
                再試行
              </button>
            </Toast>
          )}
          {!zoomTooLow && !isError && data?.truncated && (
            <Toast>表示件数の上限に達しています。地図を拡大してください。</Toast>
          )}
          {!zoomTooLow && !isError && data && !data.truncated && data.count === 0 && (
            <Toast>この範囲に図書館はありません。</Toast>
          )}
        </div>

        {selected && (
          <div className={styles.overlayPanel}>
            <LibraryPanel item={selected} onClose={() => setSelected(null)} />
          </div>
        )}

        {isFetching && <span className={styles.spinner} aria-label="読み込み中" />}
      </main>

      <footer className={styles.footer}>
        <span className={styles.status}>
          {/* ★ 地図が死んでいるのに「N 件表示中」と出すと嘘になる。
              リファラー制限違反を実際に踏んだときに気づいた（docs/07-frontend.md）。 */}
          {mapAuthFailed
            ? '地図を読み込めていません'
            : zoomTooLow
              ? `zoom ${view?.zoom.toFixed(1)} · 検索は zoom ${MIN_FETCH_ZOOM} 以上`
              : `${items.length} 件表示中${data?.truncated ? '（上限）' : ''}`}
        </span>
        {/* OpenStreetMap（ODbL）は表示義務がある。Google 側のロゴは地図に自動で出る。 */}
        <span className={styles.attribution}>
          データ: ©{' '}
          <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">
            OpenStreetMap contributors
          </a>{' '}
          (ODbL)
        </span>
      </footer>
    </div>
  )
}

/**
 * `APIProvider` を地図のある画面だけに置く。
 * マウントした時点で Maps JS の読み込みが始まるので、地図が無い画面
 * （ログイン等）にまで巻くと無駄な map load を呼ぶ（docs/07-frontend.md）。
 */
function MapArea({
  onSettled,
  onMapReady,
  authFailed,
  children,
}: {
  onSettled: (view: MapViewState) => void
  onMapReady: (map: google.maps.Map | null) => void
  authFailed: boolean
  children: React.ReactNode
}) {
  if (!env.mapEnabled) {
    return <MapPlaceholder title="地図は無効化されています" detail="VITE_MAP_ENABLED=0" />
  }
  // ★ Google 自身も地図の枠内にエラーを出すが、**ライト配色固定**で
  //   こちらのダークモードに追従しない。自分の表示に差し替える。
  if (authFailed) {
    return <MapAuthFailurePlaceholder />
  }
  if (!env.googleMapsApiKey) {
    return (
      <MapPlaceholder
        title="地図を読み込めません"
        detail="VITE_GOOGLE_MAPS_API_KEY が未設定です（.env を確認）"
      />
    )
  }

  return (
    // language / region を固定する。既定はブラウザの言語に追従するので、
    // 韓国語ブラウザだと東京の地図にハングルのラベルが出る。
    <APIProvider apiKey={env.googleMapsApiKey} language="ja" region="JP">
      <MapView onSettled={onSettled} onMapReady={onMapReady}>
        {children}
      </MapView>
    </APIProvider>
  )
}

function MapAuthFailurePlaceholder() {
  return (
    <MapPlaceholder
      title="地図を表示できません"
      detail="API キーがこのサイトからの利用を許可していません（リファラー制限 / 請求先の設定を確認）"
    />
  )
}

function Toast({ children, tone }: { children: React.ReactNode; tone?: 'error' }) {
  return (
    <p className={styles.toast} data-tone={tone}>
      {children}
    </p>
  )
}
