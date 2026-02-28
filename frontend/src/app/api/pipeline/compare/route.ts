import { NextRequest, NextResponse } from 'next/server'

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000'

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const runIds = searchParams.get('run_ids')
    const questionText = searchParams.get('question_text')

    let url = `${BACKEND_URL}/api/pipeline/compare?`
    if (runIds) {
      url += `run_ids=${runIds}`
    }
    if (questionText) {
      url += `&question_text=${encodeURIComponent(questionText)}`
    }

    const response = await fetch(url)
    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Error comparing pipeline runs:', error)
    return NextResponse.json(
      { error: 'Failed to compare pipeline runs' },
      { status: 500 }
    )
  }
}
