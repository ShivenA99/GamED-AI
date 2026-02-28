/**
 * Zone Collision Detection Hook
 *
 * Provides utility functions for detecting if a point (e.g., drop position)
 * is within a zone, supporting both circle and polygon shapes.
 */

import { useMemo, useCallback } from 'react';
import { Zone } from '../types';

/**
 * Point-in-polygon test using ray casting algorithm.
 * Returns true if the point (x, y) is inside the polygon defined by points.
 *
 * @param x - X coordinate of the point (0-100 percentage)
 * @param y - Y coordinate of the point (0-100 percentage)
 * @param polygon - Array of [x, y] coordinate pairs defining the polygon
 * @returns true if point is inside the polygon
 */
export function isPointInPolygon(
  x: number,
  y: number,
  polygon: [number, number][]
): boolean {
  if (!polygon || polygon.length < 3) return false;

  let inside = false;
  const n = polygon.length;

  for (let i = 0, j = n - 1; i < n; j = i++) {
    const [xi, yi] = polygon[i];
    const [xj, yj] = polygon[j];

    // Check if ray from point crosses edge
    if (
      ((yi > y) !== (yj > y)) &&
      (x < ((xj - xi) * (y - yi)) / (yj - yi) + xi)
    ) {
      inside = !inside;
    }
  }

  return inside;
}

/**
 * Point-in-circle test.
 * Returns true if the point (x, y) is inside the circle.
 *
 * @param x - X coordinate of the point (0-100 percentage)
 * @param y - Y coordinate of the point (0-100 percentage)
 * @param cx - Center X of the circle
 * @param cy - Center Y of the circle
 * @param radius - Radius of the circle
 * @returns true if point is inside the circle
 */
export function isPointInCircle(
  x: number,
  y: number,
  cx: number,
  cy: number,
  radius: number
): boolean {
  const dx = x - cx;
  const dy = y - cy;
  return (dx * dx + dy * dy) <= (radius * radius);
}

/**
 * Check if a point is inside a zone (supports circle, polygon, and rect shapes).
 *
 * @param x - X coordinate of the point (0-100 percentage)
 * @param y - Y coordinate of the point (0-100 percentage)
 * @param zone - The zone to check
 * @returns true if point is inside the zone
 */
export function isPointInZone(x: number, y: number, zone: Zone): boolean {
  const shape = zone.shape || 'circle';

  if (shape === 'polygon' && zone.points && zone.points.length >= 3) {
    return isPointInPolygon(x, y, zone.points);
  }

  if (shape === 'rect') {
    const zx = zone.x ?? 50;
    const zy = zone.y ?? 50;
    const r = zone.radius ?? 5;

    // Treat rect as centered on x, y with radius as half-size
    const halfWidth = r;
    const halfHeight = r;

    return (
      x >= zx - halfWidth &&
      x <= zx + halfWidth &&
      y >= zy - halfHeight &&
      y <= zy + halfHeight
    );
  }

  // Default: circle
  const zx = zone.center?.x ?? zone.x ?? 50;
  const zy = zone.center?.y ?? zone.y ?? 50;
  const radius = zone.radius ?? 5;

  return isPointInCircle(x, y, zx, zy, radius);
}

/**
 * Find the zone that contains a point.
 *
 * @param x - X coordinate (0-100 percentage)
 * @param y - Y coordinate (0-100 percentage)
 * @param zones - Array of zones to check
 * @param prioritizePolygons - If true, polygon zones take priority over circles
 * @returns The zone containing the point, or undefined if none
 */
export function findZoneAtPoint(
  x: number,
  y: number,
  zones: Zone[],
  prioritizePolygons: boolean = true
): Zone | undefined {
  if (prioritizePolygons) {
    // First check polygon zones (more precise)
    for (const zone of zones) {
      if (zone.shape === 'polygon' && zone.points && zone.points.length >= 3) {
        if (isPointInZone(x, y, zone)) {
          return zone;
        }
      }
    }

    // Then check other zones
    for (const zone of zones) {
      if (zone.shape !== 'polygon' || !zone.points || zone.points.length < 3) {
        if (isPointInZone(x, y, zone)) {
          return zone;
        }
      }
    }
  } else {
    // Check all zones in order
    for (const zone of zones) {
      if (isPointInZone(x, y, zone)) {
        return zone;
      }
    }
  }

  return undefined;
}

/**
 * Calculate the distance from a point to the center of a zone.
 * Used for determining the closest zone when multiple zones match.
 *
 * @param x - X coordinate
 * @param y - Y coordinate
 * @param zone - The zone
 * @returns Distance to zone center
 */
export function distanceToZoneCenter(x: number, y: number, zone: Zone): number {
  let zx: number, zy: number;

  if (zone.shape === 'polygon' && zone.points && zone.points.length >= 3) {
    // Use provided center or calculate from polygon points
    if (zone.center) {
      zx = zone.center.x;
      zy = zone.center.y;
    } else {
      // Calculate centroid
      const sumX = zone.points.reduce((sum, p) => sum + p[0], 0);
      const sumY = zone.points.reduce((sum, p) => sum + p[1], 0);
      zx = sumX / zone.points.length;
      zy = sumY / zone.points.length;
    }
  } else {
    zx = zone.x ?? 50;
    zy = zone.y ?? 50;
  }

  const dx = x - zx;
  const dy = y - zy;
  return Math.sqrt(dx * dx + dy * dy);
}

/**
 * Find the closest zone to a point (useful for near-miss detection).
 *
 * @param x - X coordinate
 * @param y - Y coordinate
 * @param zones - Array of zones
 * @param maxDistance - Maximum distance to consider (default: 20%)
 * @returns The closest zone within maxDistance, or undefined if none
 */
export function findClosestZone(
  x: number,
  y: number,
  zones: Zone[],
  maxDistance: number = 20
): Zone | undefined {
  let closest: Zone | undefined;
  let minDistance = maxDistance;

  for (const zone of zones) {
    const distance = distanceToZoneCenter(x, y, zone);
    if (distance < minDistance) {
      minDistance = distance;
      closest = zone;
    }
  }

  return closest;
}

/**
 * Custom hook for zone collision detection.
 * Provides memoized collision detection functions for a set of zones.
 *
 * @param zones - Array of zones to check against
 * @returns Object with collision detection functions
 */
export function useZoneCollision(zones: Zone[]) {
  // Create fast lookup map for zones by ID
  const zoneMap = useMemo(() => {
    const map = new Map<string, Zone>();
    for (const zone of zones) {
      map.set(zone.id, zone);
    }
    return map;
  }, [zones]);

  // Check if a point is in a specific zone
  const checkPointInZone = useCallback(
    (x: number, y: number, zoneId: string): boolean => {
      const zone = zoneMap.get(zoneId);
      if (!zone) return false;
      return isPointInZone(x, y, zone);
    },
    [zoneMap]
  );

  // Find zone at a point
  const getZoneAtPoint = useCallback(
    (x: number, y: number): Zone | undefined => {
      return findZoneAtPoint(x, y, zones, true);
    },
    [zones]
  );

  // Find closest zone to a point
  const getClosestZone = useCallback(
    (x: number, y: number, maxDistance: number = 20): Zone | undefined => {
      return findClosestZone(x, y, zones, maxDistance);
    },
    [zones]
  );

  // Convert pixel coordinates to percentage (requires container dimensions)
  const pixelToPercent = useCallback(
    (px: number, py: number, containerWidth: number, containerHeight: number) => {
      return {
        x: (px / containerWidth) * 100,
        y: (py / containerHeight) * 100,
      };
    },
    []
  );

  return {
    checkPointInZone,
    getZoneAtPoint,
    getClosestZone,
    pixelToPercent,
    // Export utility functions for direct use
    isPointInPolygon,
    isPointInCircle,
    isPointInZone,
  };
}

export default useZoneCollision;
