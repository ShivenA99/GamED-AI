// @ts-nocheck - matter-js types not installed (optional dependency)
'use client'

import React, { useEffect, useRef, useState } from 'react'

/**
 * PhysicsSimulation - 2D Physics simulation wrapper using Matter.js
 *
 * Provides interactive 2D physics simulations for educational games.
 * Supports projectile motion, gravity, collisions, and more.
 *
 * Library: Matter.js (MIT License)
 * Status: Stable, widely used
 */

// Note: Matter.js must be installed: npm install matter-js @types/matter-js

export interface PhysicsBody {
  id: string
  type: 'circle' | 'rectangle' | 'polygon'
  x: number
  y: number
  width?: number
  height?: number
  radius?: number
  vertices?: Array<{ x: number; y: number }>
  options?: {
    isStatic?: boolean
    restitution?: number // Bounciness (0-1)
    friction?: number
    density?: number
    frictionAir?: number
    label?: string
    render?: {
      fillStyle?: string
      strokeStyle?: string
      lineWidth?: number
    }
  }
}

export interface PhysicsSimulationProps {
  width: number
  height: number
  bodies: PhysicsBody[]
  gravity?: { x: number; y: number }
  enableMouse?: boolean
  showDebug?: boolean
  onCollision?: (bodyA: string, bodyB: string) => void
  onBodyMoved?: (bodyId: string, x: number, y: number) => void
  backgroundColor?: string
}

export function PhysicsSimulation({
  width,
  height,
  bodies,
  gravity = { x: 0, y: 1 },
  enableMouse = true,
  showDebug = false,
  onCollision,
  onBodyMoved,
  backgroundColor = '#f0f0f0',
}: PhysicsSimulationProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const engineRef = useRef<Matter.Engine | null>(null)
  const renderRef = useRef<Matter.Render | null>(null)
  const runnerRef = useRef<Matter.Runner | null>(null)
  const [isLoaded, setIsLoaded] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let Matter: typeof import('matter-js')

    const initSimulation = async () => {
      try {
        // Dynamic import of Matter.js
        Matter = await import('matter-js')

        if (!canvasRef.current) return

        // Create engine
        const engine = Matter.Engine.create()
        engine.gravity.x = gravity.x
        engine.gravity.y = gravity.y
        engineRef.current = engine

        // Create renderer
        const render = Matter.Render.create({
          canvas: canvasRef.current,
          engine: engine,
          options: {
            width,
            height,
            wireframes: showDebug,
            background: backgroundColor,
          },
        })
        renderRef.current = render

        // Create bodies
        const matterBodies: Matter.Body[] = []

        bodies.forEach((body) => {
          let matterBody: Matter.Body

          const baseOptions = {
            isStatic: body.options?.isStatic ?? false,
            restitution: body.options?.restitution ?? 0.5,
            friction: body.options?.friction ?? 0.1,
            density: body.options?.density ?? 0.001,
            frictionAir: body.options?.frictionAir ?? 0.01,
            label: body.id,
            render: {
              fillStyle: body.options?.render?.fillStyle ?? '#3B82F6',
              strokeStyle: body.options?.render?.strokeStyle ?? '#1D4ED8',
              lineWidth: body.options?.render?.lineWidth ?? 2,
            },
          }

          switch (body.type) {
            case 'circle':
              matterBody = Matter.Bodies.circle(
                body.x,
                body.y,
                body.radius || 20,
                baseOptions
              )
              break
            case 'rectangle':
              matterBody = Matter.Bodies.rectangle(
                body.x,
                body.y,
                body.width || 50,
                body.height || 50,
                baseOptions
              )
              break
            case 'polygon':
              if (body.vertices && body.vertices.length >= 3) {
                matterBody = Matter.Bodies.fromVertices(
                  body.x,
                  body.y,
                  [body.vertices],
                  baseOptions
                )
              } else {
                // Fallback to rectangle
                matterBody = Matter.Bodies.rectangle(
                  body.x,
                  body.y,
                  50,
                  50,
                  baseOptions
                )
              }
              break
            default:
              matterBody = Matter.Bodies.circle(body.x, body.y, 20, baseOptions)
          }

          matterBodies.push(matterBody)
        })

        // Add ground
        const ground = Matter.Bodies.rectangle(
          width / 2,
          height - 10,
          width,
          20,
          { isStatic: true, render: { fillStyle: '#374151' } }
        )
        matterBodies.push(ground)

        // Add walls
        const leftWall = Matter.Bodies.rectangle(
          5,
          height / 2,
          10,
          height,
          { isStatic: true, render: { fillStyle: '#374151' } }
        )
        const rightWall = Matter.Bodies.rectangle(
          width - 5,
          height / 2,
          10,
          height,
          { isStatic: true, render: { fillStyle: '#374151' } }
        )
        matterBodies.push(leftWall, rightWall)

        // Add all bodies to world
        Matter.Composite.add(engine.world, matterBodies)

        // Add mouse control
        if (enableMouse) {
          const mouse = Matter.Mouse.create(canvasRef.current)
          const mouseConstraint = Matter.MouseConstraint.create(engine, {
            mouse: mouse,
            constraint: {
              stiffness: 0.2,
              render: { visible: false },
            },
          })
          Matter.Composite.add(engine.world, mouseConstraint)
          render.mouse = mouse
        }

        // Collision events
        if (onCollision) {
          Matter.Events.on(engine, 'collisionStart', (event) => {
            event.pairs.forEach((pair) => {
              onCollision(pair.bodyA.label || 'unknown', pair.bodyB.label || 'unknown')
            })
          })
        }

        // Body position tracking
        if (onBodyMoved) {
          Matter.Events.on(engine, 'afterUpdate', () => {
            matterBodies.forEach((body) => {
              if (body.label && !body.isStatic) {
                onBodyMoved(body.label, body.position.x, body.position.y)
              }
            })
          })
        }

        // Run engine and renderer
        const runner = Matter.Runner.create()
        runnerRef.current = runner
        Matter.Runner.run(runner, engine)
        Matter.Render.run(render)

        setIsLoaded(true)
      } catch (err) {
        console.error('Failed to load Matter.js:', err)
        setError('Physics simulation requires Matter.js. Run: npm install matter-js')
      }
    }

    initSimulation()

    // Cleanup
    return () => {
      if (renderRef.current && typeof Matter !== 'undefined') {
        Matter.Render.stop(renderRef.current)
      }
      if (runnerRef.current && typeof Matter !== 'undefined') {
        Matter.Runner.stop(runnerRef.current)
      }
      if (engineRef.current && typeof Matter !== 'undefined') {
        Matter.Engine.clear(engineRef.current)
      }
    }
  }, [width, height, bodies, gravity, enableMouse, showDebug, onCollision, onBodyMoved, backgroundColor])

  if (error) {
    return (
      <div className="flex items-center justify-center p-4 bg-red-50 border border-red-200 rounded-lg">
        <p className="text-sm text-red-600">{error}</p>
      </div>
    )
  }

  return (
    <div className="relative">
      {!isLoaded && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-100 rounded-lg">
          <p className="text-gray-500">Loading physics simulation...</p>
        </div>
      )}
      <canvas
        ref={canvasRef}
        width={width}
        height={height}
        className="rounded-lg border border-gray-200"
      />
    </div>
  )
}

export default PhysicsSimulation
