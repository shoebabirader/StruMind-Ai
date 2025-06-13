import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'StruMind - Next-Generation Structural Engineering',
  description: 'Unified AI-powered structural analysis, design, and BIM platform',
  keywords: 'structural engineering, analysis, design, BIM, ETABS, STAAD, Tekla',
  authors: [{ name: 'StruMind Team' }],
  viewport: 'width=device-width, initial-scale=1',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className}>
        <div id="root">{children}</div>
      </body>
    </html>
  )
}