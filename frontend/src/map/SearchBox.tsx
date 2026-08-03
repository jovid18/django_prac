import { useEffect, useRef, useState } from 'react'

import { type LibraryListItem, type SmokingStatus, toLatLng } from '../types/api'
import styles from './SearchBox.module.css'
import { SMOKING_META } from './smoking'
import { SEARCH_LIMIT, useSearch } from './useSearch'

/** 結果を選んだときのズーム。ピンが 1 本だけ見える程度まで寄せる。 */
const PICK_ZOOM = 16

type Props = {
  /** 喫煙区分の絞り込みは検索にも掛ける（地図と結果で食い違わせない）。 */
  smoking: SmokingStatus[]
  /**
   * 地図インスタンス。**地図が無効・失敗しているときは null。**
   * その場合は移動できないが、検索と詳細パネルはそのまま使える。
   */
  map: google.maps.Map | null
  onSelect: (item: LibraryListItem) => void
}

/**
 * 名称・住所の検索ボックス。
 *
 * **都全域を検索する**（`bbox` を送らない）。結果をクリックすると
 * その館まで地図を動かして詳細パネルを開く（`api/libraries.ts`）。
 */
export function SearchBox({ smoking, map, onSelect }: Props) {
  const [input, setInput] = useState('')
  const [open, setOpen] = useState(false)
  const wrapRef = useRef<HTMLDivElement>(null)
  const { data, isFetching, isError, q } = useSearch(input, smoking)

  // 外側をクリックしたら閉じる。地図をドラッグし始めたときも閉じたい。
  useEffect(() => {
    if (!open) return
    const handle = (event: PointerEvent) => {
      if (!wrapRef.current?.contains(event.target as Node)) setOpen(false)
    }
    document.addEventListener('pointerdown', handle)
    return () => document.removeEventListener('pointerdown', handle)
  }, [open])

  const results = data?.results ?? []
  const showPanel = open && q.length > 0

  function choose(item: LibraryListItem) {
    // ★ カメラを制御（`center` / `zoom` を渡す）にせずに動かす。制御にすると
    //   操作のたびに React へ戻ってきて地図が重くなる（docs/07-frontend.md）。
    //   現在地ボタンと同じ `panTo` を使う。
    map?.panTo(toLatLng(item))
    map?.setZoom(PICK_ZOOM)
    onSelect(item)
    setOpen(false)
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
            setOpen(true)
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={(event) => {
            if (event.key === 'Escape') setOpen(false)
          }}
        />
        {input.length > 0 && (
          <button
            type="button"
            className={styles.clear}
            aria-label="検索をクリア"
            onClick={() => {
              setInput('')
              setOpen(false)
            }}
          >
            ×
          </button>
        )}
      </div>

      {showPanel && (
        <div className={styles.panel}>
          {isError ? (
            <p className={styles.message} data-tone="error">
              検索できませんでした。
            </p>
          ) : results.length === 0 ? (
            <p className={styles.message}>
              {isFetching ? '検索中…' : `「${q}」に一致する図書館はありません。`}
            </p>
          ) : (
            <>
              <ul className={styles.list}>
                {results.map((item) => (
                  <li key={item.id}>
                    <button type="button" className={styles.item} onClick={() => choose(item)}>
                      <span className={styles.itemName}>{item.name}</span>
                      <span className={styles.itemMeta}>
                        <span
                          className={styles.dot}
                          style={{ background: SMOKING_META[item.smoking_status].color }}
                          aria-hidden
                        />
                        {item.ward || '—'} · {SMOKING_META[item.smoking_status].label}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
              <p className={styles.note}>
                {/* 上限で切れていることを黙らない。一覧の `truncated` と同じ考え方。 */}
                {data?.truncated ? `上限 ${SEARCH_LIMIT} 件を表示` : `${results.length} 件`}
                ・都全域から検索（表示範囲の外を含む）
              </p>
            </>
          )}
        </div>
      )}
    </div>
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
