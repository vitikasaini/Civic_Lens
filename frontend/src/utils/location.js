/**
 * Location utilities for CivicLens:
 * - Known landmark database (sensitive locations)
 * - Nearest known location resolver
 * - Address fallback formatter ('Near <xyz>')
 */

export const KNOWN_LOCATIONS = [
  { name: 'City General Hospital', type: 'Hospital', latitude: 28.6139, longitude: 77.2090 },
  { name: 'Central Public School', type: 'School', latitude: 28.6329, longitude: 77.2195 },
  { name: 'Main Bus Terminal', type: 'Bus Stop', latitude: 28.6440, longitude: 77.2167 },
  { name: 'Central Market', type: 'Market', latitude: 28.6508, longitude: 77.2289 },
  { name: 'Municipal Corporation HQ', type: 'Government Office', latitude: 28.6353, longitude: 77.2250 },
  { name: 'City Railway Station', type: 'Railway Station', latitude: 28.6425, longitude: 77.2210 },
  { name: 'Community Temple', type: 'Religious Place', latitude: 28.6280, longitude: 77.2155 },
  { name: "Children's Park", type: 'Park/Playground', latitude: 28.6180, longitude: 77.2310 },
];

/**
 * Great-circle distance between two GPS coordinates in meters.
 */
export function haversineDistanceMeters(lat1, lon1, lat2, lon2) {
  const R = 6371000;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLon / 2) *
      Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

/**
 * Finds the nearest known sensitive location.
 */
export function getNearestKnownLocation(lat, lon) {
  if (typeof lat !== 'number' || typeof lon !== 'number' || isNaN(lat) || isNaN(lon)) {
    return null;
  }
  let closest = null;
  let minDistance = Infinity;
  for (const loc of KNOWN_LOCATIONS) {
    const d = haversineDistanceMeters(lat, lon, loc.latitude, loc.longitude);
    if (d < minDistance) {
      minDistance = d;
      closest = loc;
    }
  }
  return closest;
}

/**
 * Formats complaint location address.
 * If exact address is not present, returns 'Near <nearest known location>'.
 */
export function formatLocationAddress(address, lat, lon) {
  if (
    address &&
    typeof address === 'string' &&
    address.trim() &&
    address.trim().toLowerCase() !== 'address unavailable'
  ) {
    return address.trim();
  }
  const nearest = getNearestKnownLocation(lat, lon);
  if (nearest) {
    return `Near ${nearest.name}`;
  }
  return 'Address unavailable';
}
