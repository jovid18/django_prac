import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { addFavorite, fetchFavorites, removeFavorite } from '../api/libraries'
import type { LibraryDetail } from '../types/api'

/** お気に入り一覧。ログイン済みの画面（`/favorites`）でしか使わない。 */
export function useFavorites() {
  return useQuery({
    queryKey: ['favorites'],
    queryFn: fetchFavorites,
    // 別タブで増減しているかもしれないので、地図の一覧より短くする。
    staleTime: 10_000,
  })
}

/**
 * お気に入りの登録 / 解除。
 *
 * `mutate(next)` の `next` は**押した後にこうなってほしい状態**。
 * 「今の状態」を送らないのは、API がどちらも冪等で、連打しても
 * 最後に投げた `next` の状態に収束するため（docs/05-api.md）。
 */
export function useToggleFavorite(libraryId: number) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (next: boolean) => {
      if (next) await addFavorite(libraryId)
      else await removeFavorite(libraryId)
      return next
    },
    onSuccess: (next) => {
      // ★ 詳細は再取得せずキャッシュを直接書き換える。
      //   冪等な API なので「成功したなら next の状態になっている」と
      //   言い切れる。往復を 1 回減らせて、星の切り替わりが即座に見える。
      queryClient.setQueryData<LibraryDetail>(['library', libraryId], (prev) =>
        prev ? { ...prev, is_favorited: next } : prev,
      )
      // 一覧は行が増減するので取り直す。
      void queryClient.invalidateQueries({ queryKey: ['favorites'] })
    },
  })
}
