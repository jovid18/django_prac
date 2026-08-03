import { MapPage } from './map/MapPage'

/**
 * Day 3 時点では画面が地図 1 枚なので、そのまま描く。
 * ルーティング（/login, /favorites）は Day 4 で react-router を入れてから。
 */
function App() {
  return <MapPage />
}

export default App
