'use client'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useState } from 'react'
import { RFQCartProvider } from '../lib/rfqCartContext'
import { SearchHistoryProvider } from '../lib/searchHistoryContext'

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000, // 1 minute
            gcTime: 5 * 60 * 1000, // 5 minutes (replaces cacheTime)
          },
        },
      })
  )

  return (
    <QueryClientProvider client={queryClient}>
      <SearchHistoryProvider>
        <RFQCartProvider>
          {children}
        </RFQCartProvider>
      </SearchHistoryProvider>
    </QueryClientProvider>
  )
}