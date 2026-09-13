import { useCallback, useRef } from 'react';
import { useThree } from '@react-three/fiber';
import * as THREE from 'three';

const GLOBE_RADIUS = 2;

/**
 * Convert latitude/longitude to 3D position on sphere
 * @param {number} lat - Latitude in degrees
 * @param {number} lng - Longitude in degrees  
 * @param {number} radius - Sphere radius (default: GLOBE_RADIUS)
 * @returns {THREE.Vector3}
 */
export function latLngToVector3(lat, lng, radius = GLOBE_RADIUS) {
  const phi = (90 - lat) * (Math.PI / 180);
  const theta = (lng + 180) * (Math.PI / 180);
  const x = -(radius * Math.sin(phi) * Math.cos(theta));
  const z = radius * Math.sin(phi) * Math.sin(theta);
  const y = radius * Math.cos(phi);
  return new THREE.Vector3(x, y, z);
}

/**
 * Convert altitude (meters) to camera distance from globe center
 * Maps real-world altitude to 3D scene distances
 */
export function altitudeToDistance(altitude) {
  // Earth radius ~6371km
  // Globe radius = 2 units
  // So 1 unit ≈ 3185.5 km
  const scale = GLOBE_RADIUS / 6371;
  const realDistance = 6371 + altitude / 1000; // in km
  return realDistance * scale;
}

/**
 * Custom hook for globe camera control animations
 */
export function useGlobeControls() {
  const { camera } = useThree();
  const animationRef = useRef(null);

  const flyTo = useCallback((lat, lng, altitude = 3000, duration = 2000) => {
    // Cancel any ongoing animation
    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current);
    }

    const targetPosition = latLngToVector3(lat, lng, GLOBE_RADIUS);
    const distance = altitudeToDistance(altitude);

    // Camera position: from the surface point, move outward along the normal
    const normal = targetPosition.clone().normalize();
    const targetCameraPos = normal.multiplyScalar(distance);

    const startPosition = camera.position.clone();
    const startTime = Date.now();

    function animate() {
      const elapsed = Date.now() - startTime;
      const progress = Math.min(elapsed / duration, 1);
      
      // Ease in-out cubic
      const eased = progress < 0.5
        ? 4 * progress * progress * progress
        : 1 - Math.pow(-2 * progress + 2, 3) / 2;

      camera.position.lerpVectors(startPosition, targetCameraPos, eased);
      camera.lookAt(0, 0, 0);

      if (progress < 1) {
        animationRef.current = requestAnimationFrame(animate);
      }
    }

    animate();
  }, [camera]);

  const getCameraInfo = useCallback(() => {
    const pos = camera.position.clone();
    const distance = pos.length();
    // Convert distance back to approximate altitude
    const altitudeKm = (distance / GLOBE_RADIUS) * 6371 - 6371;
    
    // Get lat/lng from camera direction
    const direction = pos.clone().normalize();
    const lat = 90 - (Math.acos(direction.y) * 180 / Math.PI);
    const lng = (Math.atan2(direction.z, -direction.x) * 180 / Math.PI) - 180;
    const normalizedLng = ((lng + 540) % 360) - 180;

    return {
      altitude: Math.max(0, altitudeKm * 1000), // in meters
      lat,
      lng: normalizedLng,
    };
  }, [camera]);

  return { flyTo, getCameraInfo, GLOBE_RADIUS };
}
