/**
 * SatQuery AI — API Service Layer
 * 
 * Centralized service for all external API calls:
 * - Nominatim (OpenStreetMap) geocoding
 * - Overpass API for geospatial features
 * - Open Elevation API
 * - Open-Meteo weather API
 * - Backend AI query (localhost:8000)
 * - Upload & validation
 * - Tool registry
 * - Execution traces
 * - Report generation
 * 
 * All APIs are free and require no API keys.
 */

const NOMINATIM_BASE = 'https://nominatim.openstreetmap.org';
const OVERPASS_BASE = 'https://overpass-api.de/api/interpreter';
const ELEVATION_BASE = 'https://api.open-elevation.com/api/v1';
const WEATHER_BASE = 'https://api.open-meteo.com/v1/forecast';
export const BACKEND_BASE = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';


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

// ─── Backend AI Query (Legacy — used by SidePanel) ───────

/**
 * Send a query to the SatQuery AI backend (legacy endpoint)
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

// ─── Backend AI Query V2 (New Pipeline) ──────────────────

/**
 * Send a query through the new agentic pipeline
 * @param {string} query - Natural language question
 * @param {{latitude: number, longitude: number}} location - Active location
 * @param {string[]} imagePaths - Previously uploaded file paths
 * @param {File | null} imageFile - Optional inline image upload
 * @returns {Promise<object>}
 */
export async function queryBackendV2(query, location, imagePaths = [], imageFile = null) {
  try {
    const formData = new FormData();
    formData.append('query', query);
    formData.append('location', JSON.stringify(location));

    if (imagePaths.length > 0) {
      formData.append('image_paths', JSON.stringify(imagePaths));
    }

    if (imageFile) {
      formData.append('image', imageFile, imageFile.name);
    }

    const response = await fetch(`${BACKEND_BASE}/api/query`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) throw new Error('Backend unavailable');
    return await response.json();
  } catch (error) {
    console.error('[API] queryBackendV2 failed:', error);
    throw error;
  }
}

// ─── Upload Images ───────────────────────────────────────

/**
 * Upload images for validation
 * @param {File[]} files - Image files to upload
 * @param {string} modalityHints - Comma-separated modality hints
 * @returns {Promise<object>}
 */
export async function uploadImages(files, modalityHints = '') {
  try {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append('files', file, file.name);
    });
    if (modalityHints) {
      formData.append('modality_hints', modalityHints);
    }

    const response = await fetch(`${BACKEND_BASE}/api/upload`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) throw new Error('Upload failed');
    return await response.json();
  } catch (error) {
    console.error('[API] uploadImages failed:', error);
    throw error;
  }
}

// ─── Fetch Tools Registry ────────────────────────────────

/**
 * Get the list of available analysis tools
 * @returns {Promise<object>}
 */
export async function fetchTools() {
  try {
    const response = await fetch(`${BACKEND_BASE}/api/tools`);
    if (!response.ok) throw new Error('Tools fetch failed');
    return await response.json();
  } catch (error) {
    console.error('[API] fetchTools failed:', error);
    return { tools: [], total: 0 };
  }
}

// ─── Fetch Execution Trace ───────────────────────────────

/**
 * Retrieve an execution trace by query ID
 * @param {string} queryId
 * @returns {Promise<object | null>}
 */
export async function fetchTrace(queryId) {
  try {
    const response = await fetch(`${BACKEND_BASE}/api/trace/${queryId}`);
    if (!response.ok) return null;
    return await response.json();
  } catch (error) {
    console.error('[API] fetchTrace failed:', error);
    return null;
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

// ─── NASA APOD Integration ────────────────────────────────

/**
 * Fetch Astronomy Picture of the Day entries via backend proxy.
 * All NASA API keys are kept server-side only.
 * @param {object} options - { count: 10, page: 1, date: string, search: string }
 * @returns {Promise<Array<object>>}
 */
export async function fetchNasaApod({ count = 10, page = 1, date = null, search = null } = {}) {
  try {
    const params = new URLSearchParams();
    if (count) params.append('count', count);
    if (page) params.append('page', page);
    if (search) params.append('search', search);

    const url = date
      ? `${BACKEND_BASE}/api/nasa/apod/${date}`
      : `${BACKEND_BASE}/api/nasa/apod?${params}`;

    const resp = await fetch(url);
    if (!resp.ok) throw new Error(`NASA APOD fetch failed: ${resp.status}`);
    const data = await resp.json();
    return data.items || (data.item ? [data.item] : []);
  } catch (err) {
    console.error('[API] fetchNasaApod failed:', err.message);
    return [];
  }
}

/**
 * Import a NASA APOD image into the SatQuery upload workspace
 * @param {string} imageUrl
 * @param {string} title
 * @param {string} date
 */
export async function importNasaApod(imageUrl, title, date) {
  const resp = await fetch(`${BACKEND_BASE}/api/nasa/apod/import`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ image_url: imageUrl, title, date }),
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: 'Import failed' }));
    throw new Error(err.detail || 'Failed to import NASA image');
  }
  return await resp.json();
}

// ─── NVIDIA DeepSeek & Vision Integration ──────────────────

/**
 * Direct chat query with DeepSeek reasoning model
 * @param {string} message
 * @param {object} options - { systemPrompt, context, temperature, maxTokens }
 */
export async function queryDeepSeekChat(message, options = {}) {
  const resp = await fetch(`${BACKEND_BASE}/api/ai/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      system_prompt: options.systemPrompt,
      context: options.context,
      temperature: options.temperature || 1.0,
      max_tokens: options.maxTokens || 4096,
    }),
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: 'Chat failed' }));
    throw new Error(err.detail || 'DeepSeek chat request failed');
  }
  return await resp.json();
}

/**
 * Visual image processing with NVIDIA Nemotron Parse 2.0
 * @param {string} imageUrl
 * @param {object} options - { promptTokens, maxTokens }
 */
export async function parseVisionNemotron(imageUrl, options = {}) {
  const resp = await fetch(`${BACKEND_BASE}/api/ai/vision-parse`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      image_url: imageUrl,
      prompt_tokens: options.promptTokens || '</s><s><predict_bbox><predict_classes><output_markdown><predict_text_in_pic>',
      max_tokens: options.maxTokens || 2048,
    }),
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: 'Vision parse failed' }));
    throw new Error(err.detail || 'Nemotron Parse request failed');
  }
  return await resp.json();
}
