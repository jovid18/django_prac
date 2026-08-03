import type { LibraryListItem } from '../types/api'
import styles from './LibraryResultList.module.css'
import { SMOKING_META } from './smoking'

/** 距離は `nearby` のときだけ付く。検索結果には無い。 */
export type ResultItem = LibraryListItem & { distance_m?: number }

/**
 * 図書館の候補リスト。**検索結果と「近い順」の 2 か所で使う。**
 *
 * `docs/07-frontend.md` に「汎用化したいものが 2 つ以上出てから共通化する」と
 * 書いてあり、検索（Day 5 前半）に続いて `nearby` が 2 つ目になったので切り出した。
 */
export function LibraryResultList({
  items,
  note,
  onPick,
}: {
  items: ResultItem[]
  /** リストの下に出す但し書き（件数や検索範囲の説明）。 */
  note: string
  onPick: (item: ResultItem) => void
}) {
  return (
    <>
      <ul className={styles.list}>
        {items.map((item) => (
          <li key={item.id}>
            <button type="button" className={styles.item} onClick={() => onPick(item)}>
              <span className={styles.name}>{item.name}</span>
              <span className={styles.meta}>
                <span
                  className={styles.dot}
                  style={{ background: SMOKING_META[item.smoking_status].color }}
                  aria-hidden
                />
                {item.distance_m !== undefined && (
                  <span className={styles.distance}>{formatDistance(item.distance_m)}</span>
                )}
                {item.ward || '—'} · {SMOKING_META[item.smoking_status].label}
              </span>
            </button>
          </li>
        ))}
      </ul>
      <p className={styles.note}>{note}</p>
    </>
  )
}

/**
 * 1km 未満はメートル、それ以上は小数 1 桁の km。
 *
 * ⚠ export しない。**コンポーネントと関数を同じファイルから export すると**
 *   oxlint の `react/only-export-components` に引っかかる
 *   （`auth/context.ts` を分けたのと同じ理由。docs/07-frontend.md）。
 */
function formatDistance(meters: number): string {
  return meters < 1000 ? `${meters}m` : `${(meters / 1000).toFixed(1)}km`
}
