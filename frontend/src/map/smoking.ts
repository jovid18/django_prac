import type { SmokingStatus } from '../types/api'

/**
 * 喫煙区分の色とラベル。
 *
 * ★ この区分自体が練習用のダミーデータで、実在する図書館の喫煙可否とは
 *    一切関係がない（backend/apps/libraries/models.py）。
 */
export const SMOKING_META: Record<SmokingStatus, { label: string; color: string }> = {
  none: { label: '喫煙不可', color: '#7f8c8d' },
  heated_only: { label: '加熱式のみ可', color: '#2980b9' },
  cigarette_only: { label: '紙巻きのみ可', color: '#e67e22' },
  both: { label: '両方可', color: '#c0392b' },
}
