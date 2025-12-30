import type { Metadata, Viewport } from 'next'
import './globals.css'
import { Providers } from './providers'
import { ClientHeader } from '../components/ClientHeader'
import { LayoutContent } from '../components/LayoutContent'
import { ClerkProvider } from '@clerk/nextjs'

export const metadata: Metadata = {
  title: 'Sourcivity - Industrial Components Sourcing',
  description: 'AI-powered industrial components search and sourcing platform',
}

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 5,
  userScalable: true,
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <ClerkProvider
      signInFallbackRedirectUrl="/search"
      signUpFallbackRedirectUrl="/search"
    >
      <html lang="en">
        <body>
          <Providers>
            <LayoutContent>
              <ClientHeader />
              <main>
                {children}
              </main>
            </LayoutContent>
          </Providers>
        </body>
      </html>
    </ClerkProvider>
  )
}