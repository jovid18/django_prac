import { useEffect, useRef, useState } from 'react'

import { type LibraryListItem, type SmokingStatus, toLatLng } from '../types/api'
import { LibraryResultList } from './LibraryResultList'
import styles from './SearchBox.module.css'
import type { Geolocation } from './useGeolocation'
import { NEARBY_LIMIT, NEARBY_RADIUS_M, useNearby } from './useNearby'
import { SEARCH_LIMIT, useSearch } from './useSearch'

/** 結果を選んだときのズーム。ピンが 1 本だけ見える程度まで寄せる。 */
const PICK_ZOOM = 16

/** パネルに何を出しているか。`null` = 閉じている。 */
type Mode = 'search' | 'nearby' | null

type Props = {
  /** 喫煙区分の絞り込みは検索・近い順の両方に掛ける（地図と食い違わせない）。 */
  smoking: SmokingStatus[]
  /**
   * 地図インスタンス。**地図が無効・失敗しているときは null。**
   * その場合は移動できないが、検索と詳細パネルはそのまま使える。
   */
  map: google.maps.Map | null
  /** 現在地。`MapPage` が持っていて現在地ボタンと共有している。 */
  geo: Geolocation
  onSelect: (item: LibraryListItem) => void
}

/**
 * 図書館を探す口。**名称・住所の検索**と**現在地から近い順**の 2 モードを
 * 1 つのパネルで切り替える。
 *
 * 別々のパネルにしなかったのは、375px で左側に 3 段（検索・近い順・喫煙区分）
 * 積むと地図がほとんど見えなくなるため。
 */
export function SearchBox({ smoking, map, geo, onSelect }: Props) {
  const [input, setInput] = useState('')
  const [mode, setMode] = useState<Mode>(null)
  const wrapRef = useRef<HTMLDivElement>(null)

  const search = useSearch(input, smoking)
  const nearby = useNearby(geo.state, smoking, mode === 'nearby')

  // 外側をクリックしたら閉じる。地図をドラッグし始めたときも閉じたい。
  useEffect(() => {
    if (mode === null) return
    const handle = (event: PointerEvent) => {
      if (!wrapRef.current?.contains(event.target as Node)) setMode(null)
    }
    document.addEventListener('pointerdown', handle)
    return () => document.removeEventListener('pointerdown', handle)
  }, [mode])

  function choose(item: LibraryListItem) {
    // ★ カメラを制御（`center` / `zoom` を渡す）にせずに動かす。制御にすると
    //   操作のたびに React へ戻ってきて地図が重くなる（docs/07-frontend.md）。
    //   現在地ボタンと同じ `panTo` を使う。
    map?.panTo(toLatLng(item))
    map?.setZoom(PICK_ZOOM)
    onSelect(item)
    setMode(null)
  }

  return (
    <div className={styles.wrap} ref={wrapRef}>
      <div className={styles.field}>
        <SearchIcon />
        <input
          id="library-search"
          name="library-search"
          type="search"
          className={styles.input}
          value={input}
          placeholder="名称・住所で検索"
          aria-label="図書館を名称・住所で検索（都全域）"
          autoComplete="off"
          onChange={(event) => {
            setInput(event.target.value)
            setMode('search')
          }}
          onFocus={() => setMode('search')}
          onKeyDown={(event) => {
            if (event.key === 'Escape') setMode(null)
          }}
        />
        {input.length > 0 && (
          <button
            type="button"
            className={styles.clear}
            aria-label="検索をクリア"
            onClick={() => {
              setInput('')
              setMode(null)
            }}
          >
            ×
          </button>
        )}
      </div>

      {/* ★ このボタン自体が位置情報の許可を求める。起動と同時には求めない
          （地図が見えている状態で押させるほうが許可率が高い）。 */}
      <button
        type="button"
        className={styles.nearbyButton}
        data-on={mode === 'nearby' || undefined}
        disabled={geo.state.status === 'loading'}
        aria-pressed={mode === 'nearby'}
        onClick={() => {
          if (mode === 'nearby') {
            setMode(null)
            return
          }
          setMode('nearby')
          // まだ許可を得ていなければここで求める。拒否済みなら state が
          // 'denied' のままなので、下の案内文が出る。
          if (geo.state.status === 'idle' || geo.state.status === 'unavailable') geo.request()
        }}
      >
        <LocateIcon />
        {geo.state.status === 'loading' ? '現在地を取得中…' : '現在地から近い順'}
      </button>

      {mode !== null && (
        <div className={styles.panel}>
          {mode === 'search' ? (
            <SearchResults query={search} onPick={choose} />
          ) : (
            <NearbyResults geo={geo} query={nearby} onPick={choose} />
          )}
        </div>
      )}
    </div>
  )
}

function SearchResults({
  query,
  onPick,
}: {
  query: ReturnType<typeof useSearch>
  onPick: (item: LibraryListItem) => void
}) {
  const { data, isFetching, isError, q } = query

  if (q.length === 0) {
    return <p className={styles.message}>名称や住所の一部を入力してください。</p>
  }
  if (isError) {
    return (
      <p className={styles.message} data-tone="error">
        検索できませんでした。
      </p>
    )
  }

  const results = data?.results ?? []
  if (results.length === 0) {
    return (
      <p className={styles.message}>
        {isFetching ? '検索中…' : `「${q}」に一致する図書館はありません。`}
      </p>
    )
  }

  return (
    <LibraryResultList
      items={results}
      // 上限で切れていることを黙らない。一覧の `truncated` と同じ考え方。
      note={`${data?.truncated ? `上限 ${SEARCH_LIMIT} 件を表示` : `${results.length} 件`}・都全域から検索（表示範囲の外を含む）`}
      onPick={onPick}
    />
  )
}

function NearbyResults({
  geo,
  query,
  onPick,
}: {
  geo: Geolocation
  query: ReturnType<typeof useNearby>
  onPick: (item: LibraryListItem) => void
}) {
  // ★ 位置情報が無いときの案内を先に出す。ここで API を呼ばないことは
  //   `useNearby` の `enabled` が保証している（lat/lng 無しは 400）。
  if (geo.state.status === 'denied') {
    return (
      <p className={styles.message}>
        位置情報が拒否されています。ブラウザの設定から許可してください。
      </p>
    )
  }
  if (geo.state.status === 'unavailable') {
    return <p className={styles.message}>現在地を取得できませんでした。</p>
  }
  if (geo.state.status !== 'granted') {
    return <p className={styles.message}>現在地を取得しています…</p>
  }

  const { data, isPending, isError } = query

  if (isError) {
    return (
      <p className={styles.message} data-tone="error">
        近くの図書館を取得できませんでした。
      </p>
    )
  }
  if (isPending) {
    return <p className={styles.message}>検索中…</p>
  }

  const results = data?.results ?? []
  if (results.length === 0) {
    return (
      <p className={styles.message}>
        現在地から {NEARBY_RADIUS_M / 1000}km 以内に図書館はありません。
      </p>
    )
  }

  return (
    <LibraryResultList
      items={results}
      // 「N 件（上限）」はフッターの表記に合わせてある。
      note={`${results.length} 件${results.length === NEARBY_LIMIT ? '（上限）' : ''}・現在地から ${NEARBY_RADIUS_M / 1000}km 以内`}
      onPick={onPick}
    />
  )
}

function SearchIcon() {
  return (
    <svg
      className={styles.icon}
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      aria-hidden
    >
      <circle cx="10.5" cy="10.5" r="6.5" />
      <path d="M15.5 15.5 21 21" />
    </svg>
  )
}

function LocateIcon() {
  return (
    <svg
      className={styles.icon}
      width="13"
      height="13"
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
