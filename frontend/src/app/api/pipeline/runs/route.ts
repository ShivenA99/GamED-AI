import { NextRequest, NextResponse } from 'next/server'

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000'

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const limit = searchParams.get('limit') || '20'
    const topology = searchParams.get('topology')

    let url = `${BACKEND_URL}/api/pipeline/runs?limit=${limit}`
    if (topology) {
      url += `&topology=${topology}`
    }

    const response = await fetch(url)
    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Error fetching pipeline runs:', error)
    return NextResponse.json(
      { error: 'Failed to fetch pipeline runs' },
      { status: 500 }
    )
  }
}
