import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// ローカルは Vite の proxy で /api を Django に流す。
// こうするとブラウザから見て同一オリジンになり、CORS が発生しない。
// 本番（Render）はフロントと API が別ホストになるので、
// VITE_API_BASE_URL に絶対 URL を入れて CORS で通す。
//   → 差分の一覧は docs/02-architecture.md
const proxyTarget = process.env.VITE_PROXY_TARGET ?? 'http://localhost:8001'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // コンテナ内で 0.0.0.0 に bind しないとホストから見えない
    host: true,
    proxy: {
      '/api': {
        target: proxyTarget,
        changeOrigin: true,
      },
    },
  },
})
