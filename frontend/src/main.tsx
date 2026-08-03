import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router'

import App from './App.tsx'
import { AuthProvider } from './auth/AuthProvider'
import './index.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // 地図を動かすたびに叩くので、少しの間はキャッシュを使い回す
      staleTime: 60_000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        {/* 起動時に refresh を 1 回叩くので、ルータより内側でよい */}
        <AuthProvider>
          <App />
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
)
