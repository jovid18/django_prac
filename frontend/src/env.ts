/**
 * import.meta.env をここ 1 箇所でだけ読む。
 *
 * VITE_ 接頭辞の変数はビルド時にバンドルへ埋め込まれる。
 * つまりブラウザから丸見えなので、秘密の値はここに置かない。
 * Google のクライアント ID は公開前提の値なので問題ない。
 */
export const env = {
  /** ローカルは空文字（Vite の proxy に任せる）。本番は API の絶対 URL。 */
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL ?? '',
  googleClientId: import.meta.env.VITE_GOOGLE_OAUTH_CLIENT_ID ?? '',
}
