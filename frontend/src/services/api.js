/**
 * SatQuery AI — API Service Layer
 * 
 * Centralized service for all external API calls:
 * - Nominatim (OpenStreetMap) geocoding
 * - Overpass API for geospatial features
 * - Open Elevation API
 * - Open-Meteo weather API
 * - Backend AI query (localhost:8000)
 * 
 * All APIs are free and require no API keys.
 */

const NOMINATIM_BASE = 'https://nominatim.openstreetmap.org';
const OVERPASS_BASE = 'https://overpass-api.de/api/interpreter';
const ELEVATION_BASE = 'https://api.open-elevation.com/api/v1';
const WEATHER_BASE = 'https://api.open-meteo.com/v1/forecast';
const BACKEND_BASE = 'http://localhost:8000';

// Rate limiter: Nominatim requires max 1 request/second
let lastNominatimCall = 0;
async function nominatimThrottle() {
  const now = Date.now();
  const elapsed = now - lastNominatimCall;
  if (elapsed < 1100) {
    await new Promise(resolve => setTimeout(resolve, 1100 - elapsed));
  }
  lastNominatimCall = Date.now();
}

// ─── Geocoding ──────────────────────────────────────────

/**
 * Forward geocoding: place name → coordinates
 * Uses OpenStreetMap Nominatim API
 * @param {string} query - Location name (e.g., "Sriharikota Spaceport")
 * @returns {Promise<{lat: number, lng: number, displayName: string, boundingBox: number[]} | null>}
 */
export async function geocodeLocation(query) {
  try {
    await nominatimThrottle();
    const params = new URLSearchParams({
      q: query,
      format: 'json',
      limit: '1',
      addressdetails: '1',
    });
    const response = await fetch(`${NOMINATIM_BASE}/search?${params}`, {
      headers: { 'User-Agent': 'SatQueryAI/1.0' },
    });
    if (!response.ok) throw new Error(`Nominatim error: ${response.status}`);
    const results = await response.json();
    if (!results.length) return null;
    const result = results[0];
    return {
      lat: parseFloat(result.lat),
      lng: parseFloat(result.lon),
      displayName: result.display_name,
      boundingBox: result.boundingbox?.map(Number) || [],
      type: result.type,
      category: result.class,
    };
  } catch (error) {
    console.error('[API] geocodeLocation failed:', error);
    return null;
  }
}

/**
 * Reverse geocoding: coordinates → place name
 * @param {number} lat
 * @param {number} lng
 * @returns {Promise<{displayName: string, address: object} | null>}
 */
export async function reverseGeocode(lat, lng) {
  try {
    await nominatimThrottle();
    const params = new URLSearchParams({
      lat: lat.toString(),
      lon: lng.toString(),
      format: 'json',
      addressdetails: '1',
    });
    const response = await fetch(`${NOMINATIM_BASE}/reverse?${params}`, {
      headers: { 'User-Agent': 'SatQueryAI/1.0' },
    });
    if (!response.ok) throw new Error(`Nominatim reverse error: ${response.status}`);
    const result = await response.json();
    return {
      displayName: result.display_name,
      address: result.address || {},
    };
  } catch (error) {
    console.error('[API] reverseGeocode failed:', error);
    return null;
  }
}

// ─── Overpass (OSM Geospatial Features) ──────────────────

/**
 * Search for geospatial features using Overpass QL
 * @param {string} featureType - OSM feature type (e.g., "aeroway", "natural=water")
 * @param {{south: number, west: number, north: number, east: number}} bbox - Bounding box
 * @returns {Promise<Array<{id: number, lat: number, lng: number, tags: object}>>}
 */
export async function searchOverpass(featureType, bbox) {
  try {
    const { south, west, north, east } = bbox;
    const bboxStr = `${south},${west},${north},${east}`;

    // Build Overpass query based on feature type
    let filter;
    if (featureType.includes('=')) {
      const [key, value] = featureType.split('=');
      filter = `["${key}"="${value}"]`;
    } else {
      filter = `["${featureType}"]`;
    }

    const query = `
      [out:json][timeout:25];
      (
        node${filter}(${bboxStr});
        way${filter}(${bboxStr});
        relation${filter}(${bboxStr});
      );
      out center body;
    `;

    const response = await fetch(OVERPASS_BASE, {
      method: 'POST',
      body: `data=${encodeURIComponent(query)}`,
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });

    if (!response.ok) throw new Error(`Overpass error: ${response.status}`);
    const data = await response.json();

    return (data.elements || []).map(el => ({
      id: el.id,
      lat: el.lat || el.center?.lat,
      lng: el.lon || el.center?.lon,
      tags: el.tags || {},
      type: el.type,
    })).filter(el => el.lat && el.lng);
  } catch (error) {
    console.error('[API] searchOverpass failed:', error);
    return [];
  }
}

// ─── Elevation ───────────────────────────────────────────

/**
 * Fetch elevation data for a coordinate
 * @param {number} lat
 * @param {number} lng
 * @returns {Promise<number | null>} Elevation in meters
 */
export async function fetchElevation(lat, lng) {
  try {
    const params = new URLSearchParams({
      locations: `${lat},${lng}`,
    });
    const response = await fetch(`${ELEVATION_BASE}/lookup?${params}`);
    if (!response.ok) throw new Error(`Elevation error: ${response.status}`);
    const data = await response.json();
    return data.results?.[0]?.elevation ?? null;
  } catch (error) {
    console.error('[API] fetchElevation failed:', error);
    return null;
  }
}

// ─── Weather ─────────────────────────────────────────────

/**
 * Fetch current weather data for a location
 * @param {number} lat
 * @param {number} lng
 * @returns {Promise<{temperature: number, windSpeed: number, weatherCode: number, humidity: number} | null>}
 */
export async function fetchWeather(lat, lng) {
  try {
    const params = new URLSearchParams({
      latitude: lat.toString(),
      longitude: lng.toString(),
      current_weather: 'true',
      hourly: 'relativehumidity_2m',
    });
    const response = await fetch(`${WEATHER_BASE}?${params}`);
    if (!response.ok) throw new Error(`Weather error: ${response.status}`);
    const data = await response.json();
    const current = data.current_weather;
    return {
      temperature: current?.temperature,
      windSpeed: current?.windspeed,
      weatherCode: current?.weathercode,
      humidity: data.hourly?.relativehumidity_2m?.[0],
    };
  } catch (error) {
    console.error('[API] fetchWeather failed:', error);
    return null;
  }
}

// ─── Backend AI Query ────────────────────────────────────

/**
 * Send a query to the SatQuery AI backend
 * @param {string} prompt - User query
 * @param {{latitude: number, longitude: number, altitude: number}} location - Active location
 * @param {File | null} imageFile - Optional uploaded image
 * @returns {Promise<object>}
 */
export async function queryBackend(prompt, location, imageFile = null) {
  try {
    const formData = new FormData();
    formData.append('prompt', prompt);
    formData.append('location', JSON.stringify(location));

    if (imageFile) {
      formData.append('image', imageFile, imageFile.name);
    } else {
      formData.append('image_url', 'cesium-world-imagery');
    }

    const response = await fetch(`${BACKEND_BASE}/query`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) throw new Error('Backend unavailable');
    return await response.json();
  } catch (error) {
    console.error('[API] queryBackend failed:', error);
    throw error;
  }
}

// ─── Utility: Parse coordinate string ────────────────────

/**
 * Parse a coordinate string like "28.6139, 77.2090" into lat/lng
 * @param {string} value
 * @returns {{lat: number, lng: number} | null}
 */
export function parseCoordinates(value) {
  const match = value.trim().match(/^(-?\d+(?:\.\d+)?)\s*[, ]\s*(-?\d+(?:\.\d+)?)$/);
  if (!match) return null;
  const lat = Number(match[1]);
  const lng = Number(match[2]);
  if (lat < -90 || lat > 90 || lng < -180 || lng > 180) return null;
  return { lat, lng };
}

// ─── Utility: Format helpers ──────────────────────────────

export function formatCoordinate(value, positive, negative) {
  return Math.abs(value).toFixed(4) + '° ' + (value >= 0 ? positive : negative);
}

export function formatAltitude(value) {
  if (!Number.isFinite(value)) return '--';
  if (value > 1000000) return (value / 1000000).toFixed(2) + ' Mm';
  if (value > 1000) return (value / 1000).toFixed(1) + ' km';
  return Math.round(value) + ' m';
}
