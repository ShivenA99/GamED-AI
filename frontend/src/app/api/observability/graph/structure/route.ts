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
      { error: 'Failed to fetch graph structure' },
      { status: 500 }
    )
  }
}
