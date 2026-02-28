/**
 * API Route: /api/observability/graph
 *
 * Proxies to backend /api/observability/graph/structure
 * Returns the dynamic graph structure including agent metadata from the
 * centralized AGENT_METADATA_REGISTRY in backend/app/agents/instrumentation.py
 *
 * Query Parameters:
 *   - topology: string (default: "T1") - The topology to fetch
 *   - preset: string (optional) - Pipeline preset
 *
 * Response:
 *   - topology: string
 *   - preset: string
 *   - nodes: Array<{id, name, description, category, toolOrModel, icon}>
 *   - edges: Array<{from, to, type, condition?, conditionValue?, isRetryEdge?, isEscalation?}>
 *   - conditionalFunctions: Array<{name, description, outcomes}>
 */
import { NextRequest, NextResponse } from 'next/server'

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000'

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams
    const topology = searchParams.get('topology') || 'T1'
    const preset = searchParams.get('preset')

    let url = `${BACKEND_URL}/api/observability/graph/structure?topology=${topology}`
    if (preset) {
      url += `&preset=${preset}`
    }

    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
      },
      cache: 'no-store',
    })

    if (!response.ok) {
      const error = await response.text()
      console.error('[API] Backend error fetching graph:', error)
      return NextResponse.json(
        { error: `Backend error: ${error}` },
        { status: response.status }
      )
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('[API] Error fetching graph structure:', error)
    return NextResponse.json(
      { error: 'Failed to fetch graph structure from backend' },
      { status: 500 }
    )
  }
}
