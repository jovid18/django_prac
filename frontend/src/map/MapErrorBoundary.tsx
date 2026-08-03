import { Component, type ReactNode } from 'react'

type Props = { fallback: ReactNode; children: ReactNode }
type State = { failed: boolean }

/**
 * 地図まわりだけを囲むエラーバウンダリ。
 *
 * ★ 無いと**アプリ全体が真っ白（ダークモードでは真っ暗）になる**。
 *   実際に踏んだ経路: API キーのリファラー制限に引っかかると
 *   Maps の内部状態が壊れ、`<AdvancedMarker>` が
 *   `Cannot read properties of undefined (reading 'getRootNode')` を投げる。
 *   React 19 は捕まえ手がない例外でツリー全体を unmount するので、
 *   ヘッダーもフッターも消える（docs/07-frontend.md）。
 *
 *   地図は「他人のコードが自分のツリーの中で DOM を触る」箇所なので、
 *   ここだけは自前の失敗表示に落とせるようにしておく。
 */
export class MapErrorBoundary extends Component<Props, State> {
  state: State = { failed: false }

  static getDerivedStateFromError(): State {
    return { failed: true }
  }

  componentDidCatch(error: unknown) {
    // 握りつぶさない。原因を追えるようにコンソールには残す。
    console.error('[map] 地図の描画で例外が発生した', error)
  }

  render() {
    return this.state.failed ? this.props.fallback : this.props.children
  }
}
