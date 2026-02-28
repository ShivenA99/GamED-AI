import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import Link from 'next/link'
import { ThemeProvider } from '@/components/providers/ThemeProvider'
import { ThemeToggle } from '@/components/ui/ThemeToggle'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'GamED.AI - AI-Powered Educational Games',
  description: 'Transform educational questions into interactive learning games using AI',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.className} min-h-screen bg-background text-foreground antialiased`}>
        <ThemeProvider>
        {/* Skip to main content link for keyboard users */}
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-[100] focus:px-4 focus:py-2 focus:bg-[#0770A2] focus:text-white focus:rounded-lg focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#0770A2]"
        >
          Skip to main content
        </a>

        {/* Canvas-inspired Navigation */}
        <header className="canvas-nav" role="banner">
          <div className="max-w-7xl mx-auto px-4">
            <div className="flex items-center justify-between h-14">
              {/* Logo */}
              <Link href="/" className="flex items-center gap-2.5 group" aria-label="GamED.AI Home">
                <div className="w-9 h-9 bg-gradient-to-br from-[var(--canvas-primary)] to-[var(--canvas-secondary)] rounded-xl flex items-center justify-center shadow-sm group-hover:shadow-md transition-shadow" aria-hidden="true">
                  <span className="text-white text-lg">🎮</span>
                </div>
                <div className="flex flex-col">
                  <span className="text-lg font-bold text-foreground leading-none">GamED.AI</span>
                  <span className="text-[10px] text-muted-foreground font-medium uppercase tracking-wider">Educational Games</span>
                </div>
              </Link>

              {/* Navigation Links */}
              <nav className="hidden md:flex items-center gap-1" aria-label="Main navigation">
                <Link
                  href="/"
                  className="canvas-nav-link flex items-center gap-2"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                  </svg>
                  Create
                </Link>
                <Link
                  href="/games"
                  className="canvas-nav-link flex items-center gap-2"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                  </svg>
                  My Games
                </Link>
                <Link
                  href="/pipeline"
                  className="canvas-nav-link flex items-center gap-2"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                  Pipeline
                </Link>
              </nav>

              {/* Right side - Quick actions */}
              <div className="flex items-center gap-2">
                <ThemeToggle />
                <a
                  href="https://github.com/yourusername/gamed-ai"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-center w-9 h-9 rounded-lg text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                  title="View on GitHub"
                  aria-label="View source code on GitHub"
                >
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                    <path fillRule="evenodd" clipRule="evenodd" d="M12 2C6.477 2 2 6.477 2 12c0 4.42 2.865 8.17 6.839 9.49.5.092.682-.217.682-.482 0-.237-.008-.866-.013-1.7-2.782.604-3.369-1.34-3.369-1.34-.454-1.156-1.11-1.464-1.11-1.464-.908-.62.069-.608.069-.608 1.003.07 1.531 1.03 1.531 1.03.892 1.529 2.341 1.087 2.91.831.092-.646.35-1.086.636-1.336-2.22-.253-4.555-1.11-4.555-4.943 0-1.091.39-1.984 1.029-2.683-.103-.253-.446-1.27.098-2.647 0 0 .84-.269 2.75 1.025A9.578 9.578 0 0112 6.836c.85.004 1.705.114 2.504.336 1.909-1.294 2.747-1.025 2.747-1.025.546 1.377.203 2.394.1 2.647.64.699 1.028 1.592 1.028 2.683 0 3.842-2.339 4.687-4.566 4.935.359.309.678.919.678 1.852 0 1.336-.012 2.415-.012 2.743 0 .267.18.578.688.48C19.138 20.167 22 16.418 22 12c0-5.523-4.477-10-10-10z" />
                  </svg>
                </a>
              </div>
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main id="main-content" className="flex-1" role="main" tabIndex={-1}>
          {children}
        </main>

        {/* Footer */}
        <footer className="bg-card border-t border-border mt-auto" role="contentinfo">
          <div className="max-w-7xl mx-auto px-4 py-8">
            <div className="flex flex-col md:flex-row items-center justify-between gap-4">
              {/* Left - Branding */}
              <div className="flex items-center gap-2">
                <div className="w-7 h-7 bg-gradient-to-br from-[var(--canvas-primary)] to-[var(--canvas-secondary)] rounded-lg flex items-center justify-center" aria-hidden="true">
                  <span className="text-white text-sm">🎮</span>
                </div>
                <span className="text-sm font-semibold text-foreground">GamED.AI</span>
                <span className="text-xs text-muted-foreground" aria-label="Version 2.0">v2.0</span>
              </div>

              {/* Center - Links */}
              <div className="flex items-center gap-6 text-sm text-muted-foreground">
                <span>AI-Powered Educational Game Generation</span>
              </div>

              {/* Right - Status */}
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <span className="w-2 h-2 bg-green-500 rounded-full" aria-hidden="true"></span>
                <span>All systems operational</span>
              </div>
            </div>
          </div>
        </footer>
        </ThemeProvider>
      </body>
    </html>
  )
}
