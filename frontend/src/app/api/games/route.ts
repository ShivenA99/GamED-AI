import { NextRequest, NextResponse } from 'next/server'

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000'

interface ProcessData {
  id: string
  question_id?: string
  question_text?: string
  template_type?: string
  thumbnail_url?: string
  status: string
  created_at: string
}

export async function GET() {
  try {
    // Try to fetch processes from backend with timeout
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 5000) // 5 second timeout

    let response = await fetch(`${BACKEND_URL}/api/processes?limit=50`, {
      signal: controller.signal,
    })

    clearTimeout(timeoutId)

    if (response.ok) {
      const data = await response.json()
      // Transform processes to games format
      const games = (data.processes || []).map((p: ProcessData & { mechanic_type?: string; title?: string }) => ({
        process_id: p.id,
        question_id: p.question_id,
        question_text: p.question_text || 'Untitled question',
        template_type: p.template_type,
        thumbnail_url: p.thumbnail_url,
        mechanic_type: p.mechanic_type,
        title: p.title,
        status: p.status,
        created_at: p.created_at
      }))
      return NextResponse.json({ games })
    }

    // Fallback: Try to get games from observability runs
    const fallbackController = new AbortController()
    const fallbackTimeoutId = setTimeout(() => fallbackController.abort(), 5000)

    response = await fetch(`${BACKEND_URL}/api/observability/games?limit=50`, {
      signal: fallbackController.signal,
    })

    clearTimeout(fallbackTimeoutId)

    if (response.ok) {
      const data = await response.json()
      return NextResponse.json({ games: data.games || [] })
    }

    return NextResponse.json({ games: [] })
  } catch (error) {
    // Handle timeout/abort gracefully (expected when backend is down)
    if (error instanceof Error && error.name === 'AbortError') {
      // Timeout is expected when backend is down, don't log as error
      return NextResponse.json({ games: [] })
    }
    // Log other errors
    console.error('Error fetching games:', error)
    // Return empty array if backend is down or times out
    return NextResponse.json({ games: [] })
  }
}

export async function DELETE(request: NextRequest) {
  try {
    const { process_id } = await request.json()
    if (!process_id) {
      return NextResponse.json({ error: 'process_id required' }, { status: 400 })
    }

    const response = await fetch(`${BACKEND_URL}/api/processes/${process_id}`, {
      method: 'DELETE',
    })

    if (response.ok) {
      return NextResponse.json({ status: 'deleted' })
    }

    const errorData = await response.json().catch(() => ({}))
    return NextResponse.json(
      { error: errorData.detail || 'Failed to delete game' },
      { status: response.status }
    )
  } catch (error) {
    console.error('Error deleting game:', error)
    return NextResponse.json({ error: 'Failed to delete game' }, { status: 500 })
  }
}
