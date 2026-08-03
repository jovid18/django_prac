import { SMOKING_STATUSES, type SmokingStatus } from '../types/api'
import { SMOKING_META } from './smoking'
import styles from './SmokingFilter.module.css'

type Props = {
  /** 空配列 = 絞り込みなし（全件） */
  value: SmokingStatus[]
  onChange: (next: SmokingStatus[]) => void
}

/** 喫煙区分のフィルタ。凡例も兼ねる（色とラベルの対応がここで分かる）。 */
export function SmokingFilter({ value, onChange }: Props) {
  const toggle = (status: SmokingStatus) => {
    onChange(value.includes(status) ? value.filter((v) => v !== status) : [...value, status])
  }

  return (
    <div className={styles.box}>
      <div className={styles.head}>
        <span className={styles.title}>喫煙区分</span>
        {value.length > 0 && (
          <button type="button" className={styles.clear} onClick={() => onChange([])}>
            すべて表示
          </button>
        )}
      </div>

      <ul className={styles.list}>
        {SMOKING_STATUSES.map((status) => {
          const meta = SMOKING_META[status]
          const active = value.length === 0 || value.includes(status)
          return (
            <li key={status}>
              <label className={styles.item} data-dim={!active}>
                <input
                  type="checkbox"
                  checked={value.includes(status)}
                  onChange={() => toggle(status)}
                />
                <span className={styles.dot} style={{ background: meta.color }} aria-hidden />
                <span>{meta.label}</span>
              </label>
            </li>
          )
        })}
      </ul>

      <p className={styles.disclaimer}>※ ダミーデータ（実在の施設とは無関係）</p>
    </div>
  )
}
