import { useLocation, useNavigate } from 'react-router'

import { apiErrorMessage } from '../api/client'
import { useAuth } from '../auth/context'
import styles from './FavoriteButton.module.css'
import { useToggleFavorite } from './useFavorite'

type Props = {
  libraryId: number
  /** `undefined` = 詳細がまだ届いていない。星を確定させられないので押せない。 */
  isFavorited: boolean | undefined
}

/**
 * 詳細パネルのお気に入りボタン。
 *
 * 未ログインで押されたら**ログイン画面に飛ばす**（docs/07-frontend.md）。
 * 押せないように隠すのではなく、押せて導線が繋がるほうにする。
 * 戻り先を `state.from` に入れておくので、ログイン後に地図へ戻る。
 */
export function FavoriteButton({ libraryId, isFavorited }: Props) {
  const { status } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const toggle = useToggleFavorite(libraryId)

  if (status !== 'authenticated') {
    return (
      <button
        type="button"
        className={styles.button}
        // loading（起動時の refresh 待ち）の間は行き先が決まらないので押させない。
        disabled={status === 'loading'}
        onClick={() =>
          void navigate('/login', {
            state: { from: location.pathname + location.search },
          })
        }
      >
        <span aria-hidden>☆</span> お気に入り（ログインが必要）
      </button>
    )
  }

  const on = isFavorited === true

  return (
    <div className={styles.wrap}>
      <button
        type="button"
        className={styles.button}
        data-on={on || undefined}
        disabled={isFavorited === undefined || toggle.isPending}
        aria-pressed={on}
        onClick={() => toggle.mutate(!on)}
      >
        <span aria-hidden>{on ? '★' : '☆'}</span>
        {on ? 'お気に入り解除' : 'お気に入りに追加'}
      </button>
      {toggle.isError && (
        <p className={styles.error} role="alert">
          {apiErrorMessage(toggle.error, 'お気に入りを更新できませんでした。')}
        </p>
      )}
    </div>
  )
}
