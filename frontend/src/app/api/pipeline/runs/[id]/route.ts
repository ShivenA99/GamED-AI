import { NextRequest, NextResponse } from 'next/server'

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000'

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params
    const response = await fetch(`${BACKEND_URL}/api/pipeline/runs/${id}`)

    if (!response.ok) {
      return NextResponse.json(
        { error: 'Pipeline run not found' },
        { status: response.status }
      )
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Error fetching pipeline run:', error)
    return NextResponse.json(
      { error: 'Failed to fetch pipeline run' },
      { status: 500 }
    )
  }
}
