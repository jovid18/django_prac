import { useQuery } from '@tanstack/react-query'

import { fetchLibraryDetail } from '../api/libraries'
import { FavoriteButton } from '../favorites/FavoriteButton'
import type { LibraryListItem } from '../types/api'
import styles from './LibraryPanel.module.css'
import { SMOKING_META } from './smoking'

type Props = {
  /** 一覧で持っている情報。詳細の到着前でも名前を出せるようにする。 */
  item: LibraryListItem
  onClose: () => void
}

export function LibraryPanel({ item, onClose }: Props) {
  const { data, isPending, isError } = useQuery({
    queryKey: ['library', item.id],
    queryFn: () => fetchLibraryDetail(item.id),
    staleTime: 5 * 60_000,
  })

  const meta = SMOKING_META[item.smoking_status]

  return (
    <aside className={styles.panel} aria-label="図書館の詳細">
      <button type="button" className={styles.close} onClick={onClose} aria-label="閉じる">
        ×
      </button>

      <h2 className={styles.name}>{item.name}</h2>
      {data?.name_kana && <p className={styles.kana}>{data.name_kana}</p>}

      <dl className={styles.rows}>
        <dt>区市町村</dt>
        <dd>{item.ward || '—'}</dd>

        <dt>住所</dt>
        <dd>{isPending ? '読み込み中…' : data?.address || '—'}</dd>

        <dt>喫煙区分</dt>
        <dd>
          <span className={styles.badge} style={{ background: meta.color }}>
            {meta.label}
          </span>
          <span className={styles.dummy}>
            ※ このアプリの喫煙区分は開発練習用に自動生成したダミーデータで、実際の施設とは関係ありません。
          </span>
        </dd>

        {data?.website && (
          <>
            <dt>公式サイト</dt>
            <dd>
              <a href={data.website} target="_blank" rel="noreferrer">
                {data.website}
              </a>
            </dd>
          </>
        )}
      </dl>

      {isError && <p className={styles.error}>詳細を取得できませんでした。</p>}

      {/* ★ 星の状態は詳細（`is_favorited`）が持っている。届く前は
          `undefined` を渡して押せない状態にする。楽観的に「☆」を出すと、
          既に登録済みの館で一瞬「未登録」に見えてから切り替わる。 */}
      <div className={styles.favorite}>
        <FavoriteButton libraryId={item.id} isFavorited={data?.is_favorited} />
      </div>

      {/* 座標の出所を残す習慣（docs/04-data-model.md）。元プロジェクトでの
          「Google Maps 由来座標の取り扱い」に対応する練習。 */}
      {data && (
        <p className={styles.source}>
          {Number(item.latitude).toFixed(6)}, {Number(item.longitude).toFixed(6)} · 出所:{' '}
          {data.data_source}
          {data.osm_id && ` (OSM ${data.osm_id})`}
        </p>
      )}
    </aside>
  )
}
