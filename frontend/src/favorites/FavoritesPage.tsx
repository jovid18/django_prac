import { Link } from 'react-router'

import { apiErrorMessage } from '../api/client'
import { AuthMenu } from '../auth/AuthMenu'
import { SMOKING_META } from '../map/smoking'
import type { FavoriteItem } from '../types/api'
import styles from './FavoritesPage.module.css'
import { useFavorites, useToggleFavorite } from './useFavorite'

/**
 * `/favorites` — お気に入り一覧。
 *
 * **地図を描かない。** `APIProvider` を置くと map load が 1 増えるだけで、
 * ここに地図は要らない（docs/07-frontend.md「課金の単位を間違えないこと」）。
 * 代わりに一覧には住所を含めてもらっている（API 側の `FavoriteListSerializer`）。
 */
export function FavoritesPage() {
  const { data, isPending, isError, error, refetch } = useFavorites()
  const items = data?.results ?? []

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.headline}>
          <h1 className={styles.title}>お気に入り</h1>
          <AuthMenu />
        </div>
        <p className={styles.note}>
          ※ 喫煙区分は開発練習用の自動生成ダミーで、実際の施設とは関係ありません。
        </p>
      </header>

      <main className={styles.main}>
        {isPending && <p className={styles.message}>読み込み中…</p>}

        {isError && (
          <p className={styles.message} role="alert">
            {apiErrorMessage(error, 'お気に入りを取得できませんでした。')}
            <button type="button" className={styles.retry} onClick={() => void refetch()}>
              再試行
            </button>
          </p>
        )}

        {!isPending && !isError && items.length === 0 && (
          <p className={styles.message}>
            まだお気に入りがありません。
            <br />
            地図でピンを選び、詳細パネルの「お気に入りに追加」を押すとここに並びます。
          </p>
        )}

        {items.length > 0 && (
          <ul className={styles.list}>
            {items.map((item) => (
              <FavoriteRow key={item.id} item={item} />
            ))}
          </ul>
        )}
      </main>

      <footer className={styles.footer}>
        <span className={styles.status}>{items.length} 件</span>
        <Link className={styles.back} to="/">
          地図に戻る
        </Link>
        {/* OpenStreetMap（ODbL）は表示義務がある。地図が無い画面でも
            図書館データを出しているので、ここにも置く（AGENTS.md）。 */}
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

function FavoriteRow({ item }: { item: FavoriteItem }) {
  const meta = SMOKING_META[item.smoking_status]

  return (
    <li className={styles.row}>
      <div className={styles.body}>
        <h2 className={styles.name}>{item.name}</h2>
        <p className={styles.meta}>
          {[item.ward, item.address].filter(Boolean).join(' · ') || '—'}
        </p>
      </div>

      <span className={styles.badge} style={{ background: meta.color }}>
        {meta.label}
      </span>

      <RemoveButton item={item} />
    </li>
  )
}

function RemoveButton({ item }: { item: FavoriteItem }) {
  // 押した後は行そのものが消える（`useToggleFavorite` が `favorites` を invalidate する）。
  const toggle = useToggleFavorite(item.id)

  return (
    <div className={styles.action}>
      <button
        type="button"
        className={styles.remove}
        disabled={toggle.isPending}
        onClick={() => toggle.mutate(false)}
      >
        {toggle.isPending ? '解除中…' : '解除'}
      </button>
      {toggle.isError && (
        <p className={styles.error} role="alert">
          {apiErrorMessage(toggle.error, '解除できませんでした。')}
        </p>
      )}
    </div>
  )
}
