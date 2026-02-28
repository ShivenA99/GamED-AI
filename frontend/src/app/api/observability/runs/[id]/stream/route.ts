import { NextRequest, NextResponse } from 'next/server'

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000'

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params

  // Proxy the SSE stream from the backend
  const backendResponse = await fetch(
    `${BACKEND_URL}/api/observability/runs/${id}/stream`,
    {
      cache: 'no-store',
      headers: {
        'Accept': 'text/event-stream',
      },
    }
  )

  if (!backendResponse.ok) {
    return NextResponse.json(
      { error: 'Failed to connect to stream' },
      { status: backendResponse.status }
    )
  }

  // Forward the SSE stream
  return new NextResponse(backendResponse.body, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
      'X-Accel-Buffering': 'no',
    },
  })
}
