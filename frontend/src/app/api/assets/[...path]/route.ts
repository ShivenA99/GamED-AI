import { NextRequest, NextResponse } from 'next/server'

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000'

/**
 * Proxy asset requests (images, etc.) from frontend to backend
 * This allows the frontend to use relative paths like /api/assets/... 
 * which get proxied to the backend
 */
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  try {
    const { path } = await params
    const assetPath = path.join('/')
    
    // Construct backend URL
    const backendUrl = `${BACKEND_URL}/api/assets/${assetPath}`
    
    // Fetch from backend
    const response = await fetch(backendUrl, {
      headers: {
        // Forward any relevant headers
        'Accept': request.headers.get('Accept') || 'image/*',
      },
    })

    if (!response.ok) {
      return NextResponse.json(
        { error: 'Asset not found' },
        { status: response.status }
      )
    }

    // Get the content type from backend response
    const contentType = response.headers.get('content-type') || 'image/png'
    const imageBuffer = await response.arrayBuffer()

    // Return the image with proper headers
    return new NextResponse(imageBuffer, {
      status: 200,
      headers: {
        'Content-Type': contentType,
        'Cache-Control': 'public, max-age=3600',
        'Access-Control-Allow-Origin': '*',
      },
    })
  } catch (error) {
    console.error('Error proxying asset:', error)
    return NextResponse.json(
      { error: 'Failed to fetch asset' },
      { status: 500 }
    )
  }
}
