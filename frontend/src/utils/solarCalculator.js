/**
 * SatQuery AI — Solar Ephemeris & Day/Night Position Calculator
 * 
 * Computes exact subsolar coordinates, solar declination, Greenwich Hour Angle,
 * and 3D Cartesian position vector for Sun lighting and day/night transitions
 * across Earth's surface.
 */

import * as THREE from 'three';
import { latLngToVector3 } from '../hooks/useGlobeControls';

export const SUN_DISTANCE = 38; // Distance of Sun mesh and directional light in Three.js units
export const MOON_DISTANCE = 14;

/**
 * Computes the day of the year (1 - 366)
 */
export function getDayOfYear(date) {
  const start = new Date(Date.UTC(date.getUTCFullYear(), 0, 0));
  const diff = date - start;
  const oneDay = 1000 * 60 * 60 * 24;
  return Math.floor(diff / oneDay);
}

/**
 * Calculate solar declination in radians for a given Date
 * δ ≈ -23.44° * cos((360 / 365) * (N + 10))
 */
export function getSolarDeclination(date) {
  const dayOfYear = getDayOfYear(date);
  const degToRad = Math.PI / 180;
  const declinationDeg = -23.44 * Math.cos((360 / 365.25) * (dayOfYear + 10) * degToRad);
  return declinationDeg * degToRad;
}

/**
 * Calculates the Greenwich Hour Angle / subsolar longitude in degrees.
 * At 12:00:00 UTC, the sun is directly above Greenwich (0° longitude).
 * Longitude changes at 15° per hour (Earth turns 360° in 24 hours).
 * 
 * @param {Date} date - UTC Date object
 * @returns {number} Subsolar longitude in degrees [-180, 180]
 */
export function getSubsolarLongitude(date) {
  const utcHours = date.getUTCHours();
  const utcMinutes = date.getUTCMinutes();
  const utcSeconds = date.getUTCSeconds() + date.getUTCMilliseconds() / 1000;
  const fractionalHours = utcHours + utcMinutes / 60 + utcSeconds / 3600;

  // At 12 UTC, solarLng = 0°. At 00 UTC, solarLng = 180° / -180°.
  // In the Three.js spherical coordinate system used by latLngToVector3:
  // Sun moves east-to-west as time advances.
  let lng = -((fractionalHours - 12) * 15);
  while (lng > 180) lng -= 360;
  while (lng < -180) lng += 360;
  return lng;
}

/**
 * Returns complete solar position metrics for a specific Date
 */
export function calculateSolarPosition(date) {
  const radToDeg = 180 / Math.PI;
  const declinationRad = getSolarDeclination(date);
  const declinationDeg = declinationRad * radToDeg;
  const subsolarLng = getSubsolarLongitude(date);

  // Position vector pointing toward the Sun in world coordinates
  const sunPosition = latLngToVector3(declinationDeg, subsolarLng, SUN_DISTANCE);
  const sunDirection = sunPosition.clone().normalize();

  // Moon approximate counter-position with 5.14° orbital inclination
  const moonPhaseAngle = ((date.getTime() / (1000 * 60 * 60 * 24)) % 29.53) / 29.53 * Math.PI * 2;
  const moonLng = subsolarLng + 180 + (moonPhaseAngle * radToDeg);
  const moonLat = Math.sin(moonPhaseAngle) * 5.14;
  const moonPosition = latLngToVector3(moonLat, moonLng, MOON_DISTANCE);

  return {
    sunPosition,
    sunDirection,
    subsolarLat: declinationDeg,
    subsolarLng,
    moonPosition,
    moonPhaseAngle,
    date,
  };
}

/**
 * Determines whether a specific coordinate (lat, lng) is in day, twilight, or night
 * based on solar altitude angle.
 * 
 * @param {number} lat - Latitude in degrees
 * @param {number} lng - Longitude in degrees
 * @param {Date} date - UTC Date object
 * @returns {{ phase: 'day' | 'twilight' | 'night', altitudeDeg: number, solarTimeStr: string }}
 */
export function getSolarConditionAtLocation(lat, lng, date) {
  const degToRad = Math.PI / 180;
  const radToDeg = 180 / Math.PI;

  const declinationRad = getSolarDeclination(date);
  const subsolarLng = getSubsolarLongitude(date);

  // Hour angle between location longitude and subsolar longitude
  let hourAngleDeg = lng - subsolarLng;
  while (hourAngleDeg > 180) hourAngleDeg -= 360;
  while (hourAngleDeg < -180) hourAngleDeg += 360;
  const hourAngleRad = hourAngleDeg * degToRad;

  const latRad = lat * degToRad;

  // Solar altitude angle: sin(h) = sin(lat)*sin(dec) + cos(lat)*cos(dec)*cos(HA)
  const sinAltitude = Math.sin(latRad) * Math.sin(declinationRad) +
                      Math.cos(latRad) * Math.cos(declinationRad) * Math.cos(hourAngleRad);
  const altitudeDeg = Math.asin(Math.max(-1, Math.min(1, sinAltitude))) * radToDeg;

  // Local solar time calculation
  const utcHours = date.getUTCHours() + date.getUTCMinutes() / 60 + date.getUTCSeconds() / 3600;
  let localSolarHours = (utcHours + (lng / 15)) % 24;
  if (localSolarHours < 0) localSolarHours += 24;

  const h = Math.floor(localSolarHours);
  const m = Math.floor((localSolarHours - h) * 60);
  const solarTimeStr = `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;

  let phase = 'night';
  if (altitudeDeg > 0) {
    phase = 'day';
  } else if (altitudeDeg > -6) {
    phase = 'twilight'; // Civil twilight / sunrise / sunset
  } else if (altitudeDeg > -18) {
    phase = 'nautical_twilight';
  } else {
    phase = 'night';
  }

  return {
    phase,
    altitudeDeg: Math.round(altitudeDeg * 10) / 10,
    solarTimeStr,
    isNight: altitudeDeg <= -0.5,
    isDay: altitudeDeg > 0,
  };
}
