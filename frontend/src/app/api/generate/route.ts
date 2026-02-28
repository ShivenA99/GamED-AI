import { NextRequest, NextResponse } from 'next/server'

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000'
const REQUEST_TIMEOUT_MS = 30000 // 30 second timeout for initial request

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { question_text, question_options, config } = body

    // Create abort controller for timeout
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)

    // Forward to backend with timeout
    const response = await fetch(`${BACKEND_URL}/api/generate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        question_text,
        question_options,
        config,  // Pass config through
      }),
      signal: controller.signal,
    })

    clearTimeout(timeoutId)

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    // Handle timeout
    if (error instanceof Error && error.name === 'AbortError') {
      console.error('Generate request timed out')
      return NextResponse.json(
        { error: 'Request timed out. The backend may be busy or unavailable.' },
        { status: 504 }
      )
    }
    console.error('Error generating game:', error)
    return NextResponse.json(
      { error: 'Failed to generate game' },
      { status: 500 }
    )
  }
}
