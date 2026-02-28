import { NextResponse } from 'next/server'
import fs from 'fs'
import path from 'path'

export async function GET() {
  try {
    const pipelineOutputsDir = path.join(process.cwd(), '..', 'backend', 'pipeline_outputs')

    if (!fs.existsSync(pipelineOutputsDir)) {
      return NextResponse.json({ blueprints: [] })
    }

    const files = fs.readdirSync(pipelineOutputsDir)
      .filter(f => f.endsWith('.json') && f.includes('state_tracer'))
      .sort((a, b) => b.localeCompare(a)) // Most recent first

    const blueprints = files.slice(0, 10).map(filename => {
      const filepath = path.join(pipelineOutputsDir, filename)
      const content = fs.readFileSync(filepath, 'utf-8')
      const data = JSON.parse(content)

      return {
        filename,
        topology: data.topology || filename.split('_')[0],
        timestamp: data.timestamp,
        title: data.blueprint?.title || 'Untitled',
        tasks: data.blueprint?.tasks?.length || 0,
        steps: data.blueprint?.steps?.length || 0,
        blueprint: data.blueprint,
      }
    })

    return NextResponse.json({ blueprints })
  } catch (error) {
    console.error('Error loading blueprints:', error)
    return NextResponse.json({ error: 'Failed to load blueprints', blueprints: [] }, { status: 500 })
  }
}
