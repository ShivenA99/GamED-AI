'use client'

import { useState, useEffect, useMemo, useCallback } from 'react'
import Link from 'next/link'
import Image from 'next/image'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Input } from '@/components/ui/input'

interface Game {
  process_id: string
  question_id?: string
  question_text: string
  template_type: string
  thumbnail_url?: string
  mechanic_type?: string
  title?: string
  status: string
  created_at: string
}

type SortOption = 'newest' | 'oldest' | 'name_asc' | 'name_desc'
type FilterStatus = 'all' | 'completed' | 'processing' | 'error'

export default function GamesPage() {
  const [games, setGames] = useState<Game[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  // Search, filter, sort state
  const [searchQuery, setSearchQuery] = useState('')
  const [sortBy, setSortBy] = useState<SortOption>('newest')
  const [filterStatus, setFilterStatus] = useState<FilterStatus>('all')
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')

  useEffect(() => {
    const fetchGames = async () => {
      try {
        const controller = new AbortController()
        const timeoutId = setTimeout(() => controller.abort(), 6000)

        const response = await fetch('/api/games', {
          signal: controller.signal,
        })

        clearTimeout(timeoutId)

        if (response.ok) {
          const data = await response.json()
          setGames(data.games || [])
          setError(null)
        } else {
          setGames([])
          setError('Failed to load games from server.')
        }
      } catch (err) {
        setGames([])
        if (err instanceof Error) {
          if (err.name === 'AbortError') {
            setError('Backend server is not responding. Please make sure the backend is running on port 8000.')
          } else {
            setError('Cannot connect to backend server.')
          }
        }
      } finally {
        setLoading(false)
      }
    }

    fetchGames()
  }, [])

  const handleDeleteGame = useCallback(async (processId: string) => {
    if (!confirm('Are you sure you want to delete this game? This cannot be undone.')) return
    setDeletingId(processId)
    try {
      const response = await fetch('/api/games', {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ process_id: processId }),
      })
      if (response.ok) {
        setGames(prev => prev.filter(g => g.process_id !== processId))
      } else {
        const data = await response.json().catch(() => ({}))
        alert(data.error || 'Failed to delete game')
      }
    } catch {
      alert('Failed to delete game')
    } finally {
      setDeletingId(null)
    }
  }, [])

  // Filtered and sorted games
  const filteredGames = useMemo(() => {
    let result = [...games]

    // Apply search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase()
      result = result.filter(game =>
        game.question_text.toLowerCase().includes(query) ||
        game.template_type?.toLowerCase().includes(query) ||
        game.title?.toLowerCase().includes(query) ||
        game.mechanic_type?.toLowerCase().includes(query)
      )
    }

    // Apply status filter
    if (filterStatus !== 'all') {
      result = result.filter(game => game.status === filterStatus)
    }

    // Apply sorting
    result.sort((a, b) => {
      switch (sortBy) {
        case 'newest':
          return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        case 'oldest':
          return new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
        case 'name_asc':
          return a.question_text.localeCompare(b.question_text)
        case 'name_desc':
          return b.question_text.localeCompare(a.question_text)
        default:
          return 0
      }
    })

    return result
  }, [games, searchQuery, sortBy, filterStatus])

  const getStatusVariant = (status: string): 'success' | 'error' | 'info' | 'warning' => {
    switch (status) {
      case 'completed': return 'success'
      case 'error': return 'error'
      case 'processing': return 'info'
      default: return 'warning'
    }
  }

  const clearFilters = useCallback(() => {
    setSearchQuery('')
    setFilterStatus('all')
    setSortBy('newest')
  }, [])

  const hasActiveFilters = searchQuery || filterStatus !== 'all' || sortBy !== 'newest'

  // Loading skeleton
  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="flex justify-between items-center mb-8">
          <div>
            <Skeleton className="h-8 w-32 mb-2" />
            <Skeleton className="h-4 w-64" />
          </div>
          <Skeleton className="h-10 w-40" />
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
            <div key={i} className="bg-card rounded-xl border border-border overflow-hidden">
              <Skeleton className="aspect-video w-full" />
              <div className="p-4">
                <Skeleton className="h-5 w-full mb-2" />
                <Skeleton className="h-4 w-3/4 mb-3" />
                <div className="flex gap-2">
                  <Skeleton className="h-6 w-20" />
                  <Skeleton className="h-6 w-24" />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-foreground">My Games</h1>
          <p className="text-muted-foreground mt-1">
            {games.length} game{games.length !== 1 ? 's' : ''} created
          </p>
        </div>
        <Button asChild>
          <Link href="/" className="flex items-center gap-2">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
            </svg>
            Create New Game
          </Link>
        </Button>
      </div>

      {/* Search, Filter, Sort Bar */}
      <div className="bg-card border border-border rounded-xl p-4 mb-6">
        <div className="flex flex-col lg:flex-row gap-4">
          {/* Search */}
          <div className="flex-1">
            <div className="relative">
              <svg
                className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                aria-hidden="true"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              <Input
                type="text"
                placeholder="Search games by name or type..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
                aria-label="Search games"
              />
            </div>
          </div>

          {/* Filter by Status */}
          <div className="flex items-center gap-2">
            <label htmlFor="status-filter" className="text-sm text-muted-foreground whitespace-nowrap">
              Status:
            </label>
            <select
              id="status-filter"
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value as FilterStatus)}
              className="px-3 py-2 bg-background border border-input rounded-lg text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
            >
              <option value="all">All</option>
              <option value="completed">Completed</option>
              <option value="processing">Processing</option>
              <option value="error">Error</option>
            </select>
          </div>

          {/* Sort */}
          <div className="flex items-center gap-2">
            <label htmlFor="sort-by" className="text-sm text-muted-foreground whitespace-nowrap">
              Sort:
            </label>
            <select
              id="sort-by"
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as SortOption)}
              className="px-3 py-2 bg-background border border-input rounded-lg text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
            >
              <option value="newest">Newest First</option>
              <option value="oldest">Oldest First</option>
              <option value="name_asc">Name (A-Z)</option>
              <option value="name_desc">Name (Z-A)</option>
            </select>
          </div>

          {/* View Toggle */}
          <div className="flex items-center gap-1 border border-input rounded-lg p-1">
            <button
              onClick={() => setViewMode('grid')}
              className={`p-2 rounded-md transition-colors ${
                viewMode === 'grid'
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:text-foreground hover:bg-muted'
              }`}
              aria-label="Grid view"
              aria-pressed={viewMode === 'grid'}
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
              </svg>
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`p-2 rounded-md transition-colors ${
                viewMode === 'list'
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:text-foreground hover:bg-muted'
              }`}
              aria-label="List view"
              aria-pressed={viewMode === 'list'}
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
          </div>
        </div>

        {/* Active Filters */}
        {hasActiveFilters && (
          <div className="flex flex-wrap items-center gap-2 mt-4 pt-4 border-t border-border">
            <span className="text-sm text-muted-foreground">Active filters:</span>
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="inline-flex items-center gap-1 px-2 py-1 bg-primary/10 text-primary rounded-full text-xs hover:bg-primary/20 transition-colors"
              >
                Search: &quot;{searchQuery.substring(0, 20)}{searchQuery.length > 20 ? '...' : ''}&quot;
                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            )}
            {filterStatus !== 'all' && (
              <button
                onClick={() => setFilterStatus('all')}
                className="inline-flex items-center gap-1 px-2 py-1 bg-primary/10 text-primary rounded-full text-xs hover:bg-primary/20 transition-colors"
              >
                Status: {filterStatus}
                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            )}
            {sortBy !== 'newest' && (
              <button
                onClick={() => setSortBy('newest')}
                className="inline-flex items-center gap-1 px-2 py-1 bg-primary/10 text-primary rounded-full text-xs hover:bg-primary/20 transition-colors"
              >
                Sort: {sortBy.replace('_', ' ')}
                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            )}
            <button
              onClick={clearFilters}
              className="text-xs text-muted-foreground hover:text-foreground underline ml-2"
            >
              Clear all
            </button>
          </div>
        )}
      </div>

      {/* Error State */}
      {error && (
        <div className="bg-warning-bg dark:bg-warning/10 border border-warning/30 rounded-xl p-6 mb-8">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 bg-warning/20 rounded-lg flex items-center justify-center flex-shrink-0">
              <svg className="w-5 h-5 text-warning" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <div>
              <h3 className="font-semibold text-foreground mb-1">Connection Issue</h3>
              <p className="text-muted-foreground text-sm mb-3">{error}</p>
              <code className="block text-xs bg-muted text-foreground p-2 rounded-lg font-mono">
                cd backend && PYTHONPATH=. uvicorn app.main:app --reload --port 8000
              </code>
            </div>
          </div>
        </div>
      )}

      {/* Empty State */}
      {!error && games.length === 0 && (
        <div className="text-center py-16 bg-card rounded-2xl border border-border">
          <div className="w-20 h-20 bg-muted rounded-2xl flex items-center justify-center mx-auto mb-6">
            <span className="text-4xl">🎮</span>
          </div>
          <h3 className="text-xl font-semibold text-foreground mb-2">No games yet</h3>
          <p className="text-muted-foreground mb-6 max-w-sm mx-auto">
            Create your first interactive educational game by describing what you want students to learn.
          </p>
          <Button asChild size="lg">
            <Link href="/" className="flex items-center gap-2">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
              </svg>
              Create Your First Game
            </Link>
          </Button>
        </div>
      )}

      {/* No Results State */}
      {!error && games.length > 0 && filteredGames.length === 0 && (
        <div className="text-center py-16 bg-card rounded-2xl border border-border">
          <div className="w-16 h-16 bg-muted rounded-xl flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-muted-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>
          <h3 className="text-lg font-semibold text-foreground mb-2">No games found</h3>
          <p className="text-muted-foreground mb-4">
            No games match your search criteria
          </p>
          <Button variant="secondary" onClick={clearFilters}>
            Clear Filters
          </Button>
        </div>
      )}

      {/* Games Grid */}
      {!error && filteredGames.length > 0 && viewMode === 'grid' && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {filteredGames.map((game) => (
            <GameCard key={game.process_id} game={game} getStatusVariant={getStatusVariant} onDelete={handleDeleteGame} isDeleting={deletingId === game.process_id} />
          ))}
        </div>
      )}

      {/* Games List */}
      {!error && filteredGames.length > 0 && viewMode === 'list' && (
        <div className="space-y-3">
          {filteredGames.map((game) => (
            <GameListItem key={game.process_id} game={game} getStatusVariant={getStatusVariant} onDelete={handleDeleteGame} isDeleting={deletingId === game.process_id} />
          ))}
        </div>
      )}
    </div>
  )
}

// SVG placeholder for games without thumbnail images
function GamePlaceholder({ templateType, compact }: { templateType: string; compact?: boolean }) {
  const isAlgorithm = templateType === 'ALGORITHM_GAME'

  if (isAlgorithm) {
    return (
      <div className="absolute inset-0 bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center overflow-hidden">
        {/* Background grid pattern */}
        <svg className="absolute inset-0 w-full h-full opacity-[0.07]" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">
              <path d="M 20 0 L 0 0 0 20" fill="none" stroke="currentColor" strokeWidth="0.5" className="text-emerald-400" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#grid)" />
        </svg>
        {/* Code-like decoration */}
        <svg
          viewBox="0 0 200 120"
          className={`relative ${compact ? 'w-20' : 'w-32'}`}
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          {/* Terminal window frame */}
          <rect x="20" y="10" width="160" height="100" rx="8" fill="#1e293b" stroke="#334155" strokeWidth="1.5" />
          <circle cx="36" cy="22" r="3" fill="#ef4444" opacity="0.8" />
          <circle cx="48" cy="22" r="3" fill="#eab308" opacity="0.8" />
          <circle cx="60" cy="22" r="3" fill="#22c55e" opacity="0.8" />
          {/* Code lines */}
          <rect x="34" y="36" width="40" height="4" rx="2" fill="#818cf8" opacity="0.7" />
          <rect x="34" y="46" width="60" height="4" rx="2" fill="#34d399" opacity="0.5" />
          <rect x="44" y="56" width="50" height="4" rx="2" fill="#a78bfa" opacity="0.4" />
          <rect x="44" y="66" width="35" height="4" rx="2" fill="#34d399" opacity="0.5" />
          <rect x="34" y="76" width="55" height="4" rx="2" fill="#818cf8" opacity="0.4" />
          <rect x="34" y="86" width="25" height="4" rx="2" fill="#f472b6" opacity="0.5" />
          {/* Cursor blink */}
          <rect x="62" y="86" width="2" height="6" rx="1" fill="#22c55e" opacity="0.9">
            <animate attributeName="opacity" values="0.9;0.2;0.9" dur="1.2s" repeatCount="indefinite" />
          </rect>
          {/* Array visualization on the right */}
          <rect x="110" y="44" width="14" height="14" rx="2" fill="#6366f1" opacity="0.6" />
          <rect x="128" y="44" width="14" height="14" rx="2" fill="#8b5cf6" opacity="0.6" />
          <rect x="146" y="44" width="14" height="14" rx="2" fill="#a78bfa" opacity="0.6" />
          <rect x="110" y="64" width="14" height="14" rx="2" fill="#34d399" opacity="0.6" />
          <rect x="128" y="64" width="14" height="14" rx="2" fill="#6366f1" opacity="0.6" />
          <rect x="146" y="64" width="14" height="14" rx="2" fill="#8b5cf6" opacity="0.6" />
          {/* Arrow between array rows */}
          <path d="M137 60 L137 63" stroke="#94a3b8" strokeWidth="1.5" strokeLinecap="round" markerEnd="url(#arrowhead)" />
        </svg>
        {!compact && (
          <div className="absolute bottom-2 left-0 right-0 text-center">
            <span className="text-[10px] font-medium text-emerald-400/60 uppercase tracking-widest">Algorithm Game</span>
          </div>
        )}
      </div>
    )
  }

  // Interactive Diagram fallback
  return (
    <div className="absolute inset-0 bg-gradient-to-br from-sky-950 via-blue-900 to-indigo-950 flex items-center justify-center overflow-hidden">
      <svg className="absolute inset-0 w-full h-full opacity-[0.06]" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <pattern id="dots" width="16" height="16" patternUnits="userSpaceOnUse">
            <circle cx="2" cy="2" r="1" fill="currentColor" className="text-sky-300" />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#dots)" />
      </svg>
      <svg
        viewBox="0 0 200 120"
        className={`relative ${compact ? 'w-20' : 'w-32'}`}
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        {/* Diagram circles */}
        <circle cx="100" cy="35" r="18" fill="#0ea5e9" opacity="0.2" stroke="#38bdf8" strokeWidth="1.5" />
        <circle cx="55" cy="85" r="15" fill="#6366f1" opacity="0.2" stroke="#818cf8" strokeWidth="1.5" />
        <circle cx="145" cy="85" r="15" fill="#8b5cf6" opacity="0.2" stroke="#a78bfa" strokeWidth="1.5" />
        {/* Connecting lines */}
        <line x1="90" y1="50" x2="62" y2="72" stroke="#64748b" strokeWidth="1.5" strokeDasharray="4 3" opacity="0.5" />
        <line x1="110" y1="50" x2="138" y2="72" stroke="#64748b" strokeWidth="1.5" strokeDasharray="4 3" opacity="0.5" />
        <line x1="70" y1="85" x2="130" y2="85" stroke="#64748b" strokeWidth="1.5" strokeDasharray="4 3" opacity="0.5" />
        {/* Label lines */}
        <rect x="86" y="30" width="28" height="8" rx="4" fill="#38bdf8" opacity="0.6" />
        <rect x="42" y="81" width="24" height="6" rx="3" fill="#818cf8" opacity="0.5" />
        <rect x="133" y="81" width="24" height="6" rx="3" fill="#a78bfa" opacity="0.5" />
      </svg>
      {!compact && (
        <div className="absolute bottom-2 left-0 right-0 text-center">
          <span className="text-[10px] font-medium text-sky-400/60 uppercase tracking-widest">Interactive Diagram</span>
        </div>
      )}
    </div>
  )
}

// Game Card Component
function GameCard({
  game,
  getStatusVariant,
  onDelete,
  isDeleting,
}: {
  game: Game
  getStatusVariant: (status: string) => 'success' | 'error' | 'info' | 'warning'
  onDelete: (id: string) => void
  isDeleting: boolean
}) {
  const [imageError, setImageError] = useState(false)
  const thumbnailSrc = game.thumbnail_url && !imageError
    ? game.thumbnail_url
    : null

  return (
    <div className="group bg-card rounded-xl border border-border overflow-hidden hover:border-primary/50 hover:shadow-lg dark:hover:shadow-primary/5 transition-all duration-200">
      {/* Thumbnail */}
      <div className="relative aspect-video bg-muted overflow-hidden">
        {thumbnailSrc ? (
          <Image
            src={thumbnailSrc}
            alt={game.question_text}
            fill
            className="object-cover group-hover:scale-105 transition-transform duration-300"
            onError={() => setImageError(true)}
            unoptimized
          />
        ) : (
          <GamePlaceholder templateType={game.template_type} />
        )}

        {/* Hover Overlay with Play Button */}
        {game.status === 'completed' && (
          <Link
            href={`/game/${game.process_id}`}
            className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity duration-200 flex items-center justify-center"
          >
            <div className="w-14 h-14 rounded-full bg-white/90 flex items-center justify-center transform scale-90 group-hover:scale-100 transition-transform duration-200">
              <svg className="w-6 h-6 text-primary ml-1" fill="currentColor" viewBox="0 0 24 24">
                <path d="M8 5v14l11-7z" />
              </svg>
            </div>
          </Link>
        )}
      </div>

      {/* Content */}
      <div className="p-4">
        {/* Badges */}
        <div className="flex flex-wrap items-center gap-2 mb-2">
          <Badge variant={getStatusVariant(game.status)} className="text-xs">
            {game.status}
          </Badge>
          {game.template_type && (
            <Badge variant="info" className="text-xs">
              {game.template_type.replace(/_/g, ' ')}
            </Badge>
          )}
        </div>

        {/* Title */}
        <h3 className="font-medium text-foreground line-clamp-2 mb-2 min-h-[2.5rem]">
          {game.title || game.question_text}
          {game.mechanic_type && (
            <span className="text-muted-foreground font-normal text-sm"> [{game.mechanic_type.replace(/_/g, ' ')}]</span>
          )}
        </h3>

        {/* Date */}
        <p className="text-xs text-muted-foreground mb-3">
          {new Date(game.created_at).toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric'
          })}
        </p>

        {/* Actions */}
        <div className="flex gap-2">
          {game.status === 'completed' ? (
            <>
              <Button variant="success" size="sm" asChild className="flex-1">
                <Link href={`/game/${game.process_id}`} className="flex items-center justify-center gap-1">
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M8 5v14l11-7z" />
                  </svg>
                  Play
                </Link>
              </Button>
              <Button variant="secondary" size="sm" asChild>
                <Link href={`/pipeline/runs/${game.process_id}`} title="View Pipeline Dashboard">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                </Link>
              </Button>
            </>
          ) : game.status === 'processing' ? (
            <Button variant="secondary" size="sm" asChild className="flex-1">
              <Link href={`/pipeline/runs/${game.process_id}`} className="flex items-center justify-center gap-1">
                <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                View Dashboard
              </Link>
            </Button>
          ) : game.status === 'error' ? (
            <Button variant="secondary" size="sm" asChild className="flex-1">
              <Link href={`/pipeline/runs/${game.process_id}`} className="flex items-center justify-center gap-1">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
                View Dashboard
              </Link>
            </Button>
          ) : (
            <Button variant="secondary" size="sm" className="flex-1" disabled>
              Unavailable
            </Button>
          )}
          <Button
            variant="secondary"
            size="sm"
            onClick={() => onDelete(game.process_id)}
            disabled={isDeleting}
            title="Delete game"
            className="text-red-500 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-950"
          >
            {isDeleting ? (
              <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            ) : (
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            )}
          </Button>
        </div>
      </div>
    </div>
  )
}

// Game List Item Component
function GameListItem({
  game,
  getStatusVariant,
  onDelete,
  isDeleting,
}: {
  game: Game
  getStatusVariant: (status: string) => 'success' | 'error' | 'info' | 'warning'
  onDelete: (id: string) => void
  isDeleting: boolean
}) {
  const [imageError, setImageError] = useState(false)
  const thumbnailSrc = game.thumbnail_url && !imageError
    ? game.thumbnail_url
    : null

  return (
    <div className="group bg-card rounded-xl border border-border overflow-hidden hover:border-primary/50 hover:shadow-md transition-all">
      <div className="flex items-center gap-4 p-4">
        {/* Thumbnail */}
        <div className="relative w-24 h-16 rounded-lg overflow-hidden bg-muted flex-shrink-0">
          {thumbnailSrc ? (
            <Image
              src={thumbnailSrc}
              alt={game.question_text}
              fill
              className="object-cover"
              onError={() => setImageError(true)}
              unoptimized
            />
          ) : (
            <GamePlaceholder templateType={game.template_type} compact />
          )}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2 mb-1">
            <Badge variant={getStatusVariant(game.status)} className="text-xs">
              {game.status}
            </Badge>
            {game.template_type && (
              <Badge variant="info" className="text-xs">
                {game.template_type.replace(/_/g, ' ')}
              </Badge>
            )}
          </div>
          <h3 className="font-medium text-foreground truncate">
            {game.title || game.question_text}
            {game.mechanic_type && (
              <span className="text-muted-foreground font-normal text-sm"> [{game.mechanic_type.replace(/_/g, ' ')}]</span>
            )}
          </h3>
          <p className="text-xs text-muted-foreground">
            {new Date(game.created_at).toLocaleDateString('en-US', {
              month: 'short',
              day: 'numeric',
              year: 'numeric',
              hour: '2-digit',
              minute: '2-digit'
            })}
          </p>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2 flex-shrink-0">
          {game.status === 'completed' ? (
            <>
              <Button variant="success" size="sm" asChild>
                <Link href={`/game/${game.process_id}`} className="flex items-center gap-1">
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M8 5v14l11-7z" />
                  </svg>
                  Play
                </Link>
              </Button>
              <Button variant="secondary" size="sm" asChild>
                <Link href={`/pipeline/runs/${game.process_id}`} className="flex items-center gap-1">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                  Dashboard
                </Link>
              </Button>
            </>
          ) : (game.status === 'processing' || game.status === 'error') ? (
            <Button variant="secondary" size="sm" asChild>
              <Link href={`/pipeline/runs/${game.process_id}`} className="flex items-center gap-1">
                {game.status === 'processing' && (
                  <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                )}
                {game.status === 'error' && (
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                )}
                View Dashboard
              </Link>
            </Button>
          ) : null}
          <Button
            variant="secondary"
            size="sm"
            onClick={() => onDelete(game.process_id)}
            disabled={isDeleting}
            title="Delete game"
            className="text-red-500 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-950"
          >
            {isDeleting ? (
              <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            ) : (
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            )}
          </Button>
        </div>
      </div>
    </div>
  )
}
