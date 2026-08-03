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

  /**
   * Maps JavaScript API のキー。
   *
   * ⚠ OAuth クライアント ID と違い、**これは課金に直結する公開値**。
   *   バンドルから誰でも読めるので、Google Cloud 側で
   *   「HTTP リファラー制限 + Maps JavaScript API だけに絞る」を必ず設定する。
   *   制限を掛けないと他人が自分の請求先で呼べてしまう（docs/00-decisions.md）。
   */
  googleMapsApiKey: import.meta.env.VITE_GOOGLE_MAPS_API_KEY ?? '',

  /**
   * Map ID。Advanced Markers を使うのに必須で、地図のスタイルもここに紐づく。
   * ローカルは Google が用意している `DEMO_MAP_ID` で足りる。
   */
  //
  // ⚠ `??` ではなく `||` を使う。docker compose は未設定の変数を
  //   **空文字**として渡すので（`${GOOGLE_MAPS_MAP_ID:-}`）、`??` では
  //   フォールバックが効かず `mapId=""` になる。その状態だと Google が
  //   「有効なマップ ID を使用せずに地図が初期化されています」を出し続け、
  //   Advanced Markers が動かない（実際に踏んだ）。
  googleMapsMapId: import.meta.env.VITE_GOOGLE_MAPS_MAP_ID || 'DEMO_MAP_ID',

  /**
   * 地図を描くかどうか。`VITE_MAP_ENABLED=0` でプレースホルダに差し替える。
   *
   * 課金単位は「map load（地図インスタンスの生成回数）」で、**開発中の
   * 保存・リロードが最大の消費者**になる。フィルタやパネルの UI を触っている間は
   * 地図が要らないので、そのときはこれを 0 にする（docs/07-frontend.md）。
   */
  mapEnabled: import.meta.env.VITE_MAP_ENABLED !== '0',
}
