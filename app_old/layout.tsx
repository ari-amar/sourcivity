import type { Metadata } from 'next'
import './globals.css'
import { Providers } from './providers'
import { ClientHeader } from '../components/ClientHeader'

export const metadata: Metadata = {
  title: 'SourceFlow - Industrial Parts Sourcing',
  description: 'AI-powered industrial parts search and sourcing platform',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>
        <Providers>
          <div className="min-h-screen bg-background">
            <ClientHeader />
            <main>
              {children}
            </main>
          </div>
        </Providers>
      </body>
    </html>
  )
}