import { NextRequest, NextResponse } from 'next/server'

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000'

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id: processId } = await params

    // Get status from backend
    const statusResponse = await fetch(`${BACKEND_URL}/api/generate/${processId}/status`)

    if (!statusResponse.ok) {
      return NextResponse.json(
        { error: 'Process not found', status: 'failed' },
        { status: statusResponse.status }
      )
    }

    const statusData = await statusResponse.json()

    // Map status for frontend
    let mappedStatus = statusData.status
    if (mappedStatus === 'processing') mappedStatus = 'running'
    if (mappedStatus === 'error') mappedStatus = 'failed'

    // If completed, fetch the blueprint
    let blueprint = null
    if (statusData.status === 'completed') {
      try {
        const blueprintResponse = await fetch(`${BACKEND_URL}/api/generate/${processId}/blueprint`)
        if (blueprintResponse.ok) {
          const blueprintData = await blueprintResponse.json()
          blueprint = blueprintData.blueprint
        }
      } catch (e) {
        console.error('Error fetching blueprint:', e)
      }
    }

    return NextResponse.json({
      status: mappedStatus,
      current_step: statusData.current_agent,
      blueprint: blueprint,
      error: statusData.error_message
    })
  } catch (error) {
    console.error('Error fetching status:', error)
    return NextResponse.json(
      { error: 'Failed to fetch status', status: 'failed' },
      { status: 500 }
    )
  }
}
