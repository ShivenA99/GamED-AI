// @ts-nocheck - Leaflet types not installed (optional dependency)
'use client'

import React, { useEffect, useRef, useState } from 'react'

/**
 * InteractiveMap - Geography and location-based visualization component
 *
 * Provides interactive map functionality for educational geography games.
 * Uses Leaflet (BSD-2 License) for mapping.
 *
 * To enable full functionality, install:
 * npm install leaflet react-leaflet @types/leaflet
 */

export interface MapMarker {
  id: string
  lat: number
  lng: number
  label: string
  color?: string
  popup?: string
}

export interface MapRegion {
  id: string
  name: string
  coordinates: Array<[number, number]>
  color?: string
  fillOpacity?: number
}

export interface InteractiveMapProps {
  center: [number, number]
  zoom: number
  markers?: MapMarker[]
  regions?: MapRegion[]
  width?: number | string
  height?: number
  onMarkerClick?: (marker: MapMarker) => void
  onRegionClick?: (region: MapRegion) => void
  showZoomControls?: boolean
  draggable?: boolean
}

export function InteractiveMap({
  center,
  zoom,
  markers = [],
  regions = [],
  width = '100%',
  height = 400,
  onMarkerClick,
  onRegionClick,
  showZoomControls = true,
  draggable = true,
}: InteractiveMapProps) {
  const mapRef = useRef<HTMLDivElement>(null)
  const [isLoaded, setIsLoaded] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedMarker, setSelectedMarker] = useState<MapMarker | null>(null)

  useEffect(() => {
    const initMap = async () => {
      try {
        // Dynamic import of Leaflet
        const L = await import('leaflet')
        await import('leaflet/dist/leaflet.css')

        if (!mapRef.current) return

        // Clear any existing map
        mapRef.current.innerHTML = ''

        // Create map
        const map = L.map(mapRef.current, {
          center: center,
          zoom: zoom,
          zoomControl: showZoomControls,
          dragging: draggable,
        })

        // Add tile layer (OpenStreetMap)
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
          attribution: '&copy; OpenStreetMap contributors',
        }).addTo(map)

        // Add markers
        markers.forEach((marker) => {
          const icon = L.divIcon({
            className: 'custom-marker',
            html: `<div style="
              background-color: ${marker.color || '#3B82F6'};
              width: 24px;
              height: 24px;
              border-radius: 50%;
              border: 2px solid white;
              box-shadow: 0 2px 4px rgba(0,0,0,0.3);
            "></div>`,
            iconSize: [24, 24],
            iconAnchor: [12, 12],
          })

          const leafletMarker = L.marker([marker.lat, marker.lng], { icon }).addTo(map)

          if (marker.popup) {
            leafletMarker.bindPopup(marker.popup)
          } else {
            leafletMarker.bindPopup(marker.label)
          }

          leafletMarker.on('click', () => {
            onMarkerClick?.(marker)
          })
        })

        // Add regions
        regions.forEach((region) => {
          const polygon = L.polygon(region.coordinates as L.LatLngExpression[], {
            color: region.color || '#3B82F6',
            fillColor: region.color || '#3B82F6',
            fillOpacity: region.fillOpacity || 0.3,
          }).addTo(map)

          polygon.bindPopup(region.name)

          polygon.on('click', () => {
            onRegionClick?.(region)
          })
        })

        setIsLoaded(true)
      } catch (err) {
        console.error('Failed to load Leaflet:', err)
        setError('Map requires Leaflet. Run: npm install leaflet react-leaflet @types/leaflet')
      }
    }

    initMap()

    return () => {
      if (mapRef.current) {
        mapRef.current.innerHTML = ''
      }
    }
  }, [center, zoom, markers, regions, showZoomControls, draggable, onMarkerClick, onRegionClick])

  // Fallback: Simple SVG map placeholder
  if (error) {
    return (
      <div
        style={{ width, height }}
        className="relative bg-blue-50 border border-blue-200 rounded-lg overflow-hidden"
      >
        {/* Simple world map placeholder */}
        <svg
          viewBox="0 0 1000 500"
          className="w-full h-full"
          preserveAspectRatio="xMidYMid meet"
        >
          {/* Ocean background */}
          <rect width="1000" height="500" fill="#BFDBFE" />

          {/* Simple continent shapes */}
          <ellipse cx="200" cy="200" rx="150" ry="100" fill="#BBF7D0" />
          <ellipse cx="350" cy="250" rx="100" ry="120" fill="#BBF7D0" />
          <ellipse cx="550" cy="200" rx="180" ry="130" fill="#BBF7D0" />
          <ellipse cx="800" cy="230" rx="120" ry="100" fill="#BBF7D0" />
          <ellipse cx="850" cy="380" rx="100" ry="60" fill="#BBF7D0" />

          {/* Markers */}
          {markers.map((marker, i) => {
            // Simple lat/lng to x/y conversion
            const x = ((marker.lng + 180) / 360) * 1000
            const y = ((90 - marker.lat) / 180) * 500

            return (
              <g key={marker.id} onClick={() => onMarkerClick?.(marker)} className="cursor-pointer">
                <circle
                  cx={x}
                  cy={y}
                  r={8}
                  fill={marker.color || '#3B82F6'}
                  stroke="white"
                  strokeWidth={2}
                />
                <text
                  x={x + 12}
                  y={y + 4}
                  className="text-xs fill-gray-700"
                >
                  {marker.label}
                </text>
              </g>
            )
          })}
        </svg>

        {/* Error message */}
        <div className="absolute bottom-2 left-2 right-2 p-2 bg-amber-50 border border-amber-200 rounded text-xs text-amber-700">
          {error}
        </div>

        {/* Selected marker popup */}
        {selectedMarker && (
          <div className="absolute top-2 left-2 p-2 bg-white border border-gray-200 rounded shadow-lg">
            <p className="text-sm font-medium">{selectedMarker.label}</p>
            {selectedMarker.popup && (
              <p className="text-xs text-gray-600">{selectedMarker.popup}</p>
            )}
          </div>
        )}
      </div>
    )
  }

  return (
    <div style={{ width, height }} className="relative rounded-lg overflow-hidden">
      {!isLoaded && (
        <div className="absolute inset-0 flex items-center justify-center bg-blue-50">
          <p className="text-gray-500">Loading map...</p>
        </div>
      )}
      <div ref={mapRef} style={{ width: '100%', height: '100%' }} />
    </div>
  )
}

export default InteractiveMap
