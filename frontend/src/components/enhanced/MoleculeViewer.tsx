// @ts-nocheck - 3Dmol types not installed (optional dependency)
'use client'

import React, { useEffect, useRef, useState } from 'react'

/**
 * MoleculeViewer - 3D molecular visualization component
 *
 * Provides 3D molecular visualization for chemistry education.
 * Uses 3Dmol.js (BSD License) for rendering.
 *
 * To enable full functionality, install:
 * npm install 3dmol
 */

export interface MoleculeViewerProps {
  // Molecule data (PDB, SDF, MOL2, XYZ format)
  data?: string
  format?: 'pdb' | 'sdf' | 'mol2' | 'xyz' | 'cif'

  // Or fetch from PDB
  pdbId?: string

  // Display options
  width?: number
  height?: number
  style?: 'stick' | 'sphere' | 'cartoon' | 'surface' | 'line'
  backgroundColor?: string
  spin?: boolean

  // Interaction
  onAtomClick?: (atom: { elem: string; x: number; y: number; z: number }) => void
}

export function MoleculeViewer({
  data,
  format = 'pdb',
  pdbId,
  width = 400,
  height = 300,
  style = 'stick',
  backgroundColor = '#000000',
  spin = false,
  onAtomClick,
}: MoleculeViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [isLoaded, setIsLoaded] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [moleculeName, setMoleculeName] = useState<string>('')

  useEffect(() => {
    const init3Dmol = async () => {
      try {
        // Dynamic import of 3Dmol.js
        const $3Dmol = (await import('3dmol')).default

        if (!containerRef.current) return

        // Create viewer
        const viewer = $3Dmol.createViewer(containerRef.current, {
          backgroundColor,
          id: 'mol-viewer',
        })

        // Load molecule data
        let moleculeData = data

        if (pdbId) {
          // Fetch from PDB
          const response = await fetch(
            `https://files.rcsb.org/download/${pdbId}.pdb`
          )
          if (!response.ok) throw new Error(`Failed to fetch PDB ${pdbId}`)
          moleculeData = await response.text()
          setMoleculeName(pdbId.toUpperCase())
        }

        if (!moleculeData) {
          throw new Error('No molecule data provided')
        }

        // Add model
        viewer.addModel(moleculeData, format)

        // Set style
        const styleSpec: { [key: string]: object } = {
          stick: { stick: {} },
          sphere: { sphere: { scale: 0.5 } },
          cartoon: { cartoon: { color: 'spectrum' } },
          surface: { surface: { opacity: 0.8 } },
          line: { line: {} },
        }
        viewer.setStyle({}, styleSpec[style] || styleSpec.stick)

        // Zoom to fit
        viewer.zoomTo()

        // Enable spin
        if (spin) {
          viewer.spin(true)
        }

        // Click handling
        if (onAtomClick) {
          viewer.setClickable({}, true, (atom: { elem: string; x: number; y: number; z: number }) => {
            onAtomClick(atom)
          })
        }

        // Render
        viewer.render()

        setIsLoaded(true)
      } catch (err) {
        console.error('Failed to load 3Dmol.js:', err)
        setError('Molecule viewer requires 3Dmol.js. Run: npm install 3dmol')
      }
    }

    init3Dmol()
  }, [data, format, pdbId, style, backgroundColor, spin, onAtomClick])

  // Fallback: Simple 2D representation
  if (error) {
    return (
      <div
        style={{ width, height }}
        className="relative bg-gray-900 border border-gray-700 rounded-lg overflow-hidden"
      >
        {/* Simple atom representation */}
        <svg
          viewBox="0 0 200 200"
          className="w-full h-full"
          preserveAspectRatio="xMidYMid meet"
        >
          {/* Central atom */}
          <circle cx="100" cy="100" r="30" fill="#3B82F6" />
          <text x="100" y="105" textAnchor="middle" fill="white" fontSize="16">
            C
          </text>

          {/* Surrounding atoms */}
          <circle cx="50" cy="60" r="20" fill="#EF4444" />
          <text x="50" y="65" textAnchor="middle" fill="white" fontSize="12">
            O
          </text>
          <line x1="70" y1="75" x2="80" y2="85" stroke="white" strokeWidth="2" />

          <circle cx="150" cy="60" r="20" fill="#10B981" />
          <text x="150" y="65" textAnchor="middle" fill="white" fontSize="12">
            N
          </text>
          <line x1="130" y1="75" x2="120" y2="85" stroke="white" strokeWidth="2" />

          <circle cx="60" cy="150" r="15" fill="white" />
          <text x="60" y="155" textAnchor="middle" fill="gray" fontSize="10">
            H
          </text>
          <line x1="75" y1="135" x2="85" y2="120" stroke="white" strokeWidth="2" />

          <circle cx="140" cy="150" r="15" fill="white" />
          <text x="140" y="155" textAnchor="middle" fill="gray" fontSize="10">
            H
          </text>
          <line x1="125" y1="135" x2="115" y2="120" stroke="white" strokeWidth="2" />
        </svg>

        {/* Error message */}
        <div className="absolute bottom-2 left-2 right-2 p-2 bg-amber-900/80 border border-amber-600 rounded text-xs text-amber-200">
          {error}
        </div>

        {/* Molecule name */}
        {moleculeName && (
          <div className="absolute top-2 left-2 px-2 py-1 bg-white/10 rounded text-white text-xs">
            {moleculeName}
          </div>
        )}
      </div>
    )
  }

  return (
    <div style={{ width, height }} className="relative rounded-lg overflow-hidden">
      {!isLoaded && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-900">
          <p className="text-gray-400">Loading molecule...</p>
        </div>
      )}
      <div ref={containerRef} style={{ width: '100%', height: '100%' }} />

      {/* Controls */}
      {isLoaded && (
        <div className="absolute bottom-2 right-2 flex gap-1">
          <button
            className="p-1 bg-white/10 rounded text-white text-xs hover:bg-white/20"
            title="Reset view"
          >
            Reset
          </button>
        </div>
      )}

      {/* Molecule name */}
      {moleculeName && isLoaded && (
        <div className="absolute top-2 left-2 px-2 py-1 bg-white/10 rounded text-white text-xs">
          {moleculeName}
        </div>
      )}
    </div>
  )
}

export default MoleculeViewer
