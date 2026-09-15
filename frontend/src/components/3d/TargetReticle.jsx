import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { latLngToVector3 } from '../../hooks/useGlobeControls';

const GLOBE_RADIUS = 2;

/**
 * 3D Holographic Target Reticle for EarthGlobe
 * Displays rotating cybernetic brackets, pulsing target rings,
 * and a vertical orbital lock laser beam.
 */
export default function TargetReticle({
  lat,
  lng,
  globeState = 'location_locked',
}) {
  const groupRef = useRef();
  const outerRingRef = useRef();
  const innerRingRef = useRef();
  const beamRef = useRef();
  const pulseRingRef = useRef();

  // Position on globe surface
  const position = useMemo(() => {
    return latLngToVector3(lat, lng, GLOBE_RADIUS + 0.015);
  }, [lat, lng]);

  // Orientation: align reticle plane tangent to globe sphere
  const orientation = useMemo(() => {
    const normal = position.clone().normalize();
    const q = new THREE.Quaternion();
    q.setFromUnitVectors(new THREE.Vector3(0, 0, 1), normal);
    return q;
  }, [position]);

  // Color scheme based on globeState
  const color = useMemo(() => {
    switch (globeState) {
      case 'processing':
        return '#f59e0b'; // Amber
      case 'location_found':
        return '#10b981'; // Emerald
      case 'location_locked':
        return '#06b6d4'; // Cyan / ISRO Blue
      case 'location_unknown':
        return '#ef4444'; // Crimson
      default:
        return '#38bdf8'; // Sky Blue
    }
  }, [globeState]);

  // Animation frame loop
  useFrame((_, delta) => {
    const time = performance.now() * 0.001;

    // Outer ring clockwise rotation
    if (outerRingRef.current) {
      const speed = globeState === 'processing' ? 3.5 : 1.2;
      outerRingRef.current.rotation.z += delta * speed;
    }

    // Inner ring counter-clockwise rotation
    if (innerRingRef.current) {
      const speed = globeState === 'processing' ? -4.0 : -1.8;
      innerRingRef.current.rotation.z += delta * speed;
    }

    // Radar pulse wave expansion
    if (pulseRingRef.current) {
      const cycle = (time * 1.5) % 1;
      const scale = 0.5 + cycle * 1.8;
      pulseRingRef.current.scale.set(scale, scale, 1);
      if (pulseRingRef.current.material) {
        pulseRingRef.current.material.opacity = Math.max(0, (1 - cycle) * 0.6);
      }
    }

    // Vertical targeting beam shimmer
    if (beamRef.current) {
      const pulse = 0.7 + Math.sin(time * 6) * 0.3;
      beamRef.current.material.opacity = 0.4 * pulse;
    }
  });

  return (
    <group position={position} quaternion={orientation} ref={groupRef}>
      {/* Central Core Point */}
      <mesh position={[0, 0, 0.002]}>
        <sphereGeometry args={[0.012, 16, 16]} />
        <meshBasicMaterial color={color} />
      </mesh>

      {/* Pulsing expanding sonar radar wave */}
      <mesh ref={pulseRingRef} position={[0, 0, 0.001]}>
        <ringGeometry args={[0.04, 0.048, 32]} />
        <meshBasicMaterial
          color={color}
          transparent
          opacity={0.5}
          side={THREE.DoubleSide}
        />
      </mesh>

      {/* Outer Segmented HUD Ring */}
      <mesh ref={outerRingRef} position={[0, 0, 0.003]}>
        <ringGeometry args={[0.055, 0.065, 24, 1, 0, Math.PI * 1.8]} />
        <meshBasicMaterial
          color={color}
          transparent
          opacity={0.85}
          side={THREE.DoubleSide}
        />
      </mesh>

      {/* Inner Precision Target Ring */}
      <mesh ref={innerRingRef} position={[0, 0, 0.004]}>
        <ringGeometry args={[0.028, 0.034, 16, 1, 0, Math.PI * 1.6]} />
        <meshBasicMaterial
          color={color}
          transparent
          opacity={0.9}
          side={THREE.DoubleSide}
        />
      </mesh>

      {/* 4 Cardinal Crosshair Brackets */}
      {[-0.045, 0.045].map((x, i) => (
        <mesh key={`bracket-x-${i}`} position={[x, 0, 0.005]}>
          <planeGeometry args={[0.018, 0.003]} />
          <meshBasicMaterial color={color} />
        </mesh>
      ))}
      {[-0.045, 0.045].map((y, i) => (
        <mesh key={`bracket-y-${i}`} position={[0, y, 0.005]}>
          <planeGeometry args={[0.003, 0.018]} />
          <meshBasicMaterial color={color} />
        </mesh>
      ))}

      {/* Orbital Beam from Surface to Space */}
      <mesh
        ref={beamRef}
        position={[0, 0, 0.35]}
        rotation={[Math.PI / 2, 0, 0]}
      >
        <cylinderGeometry args={[0.003, 0.014, 0.7, 12, 1, true]} />
        <meshBasicMaterial
          color={color}
          transparent
          opacity={0.4}
          side={THREE.DoubleSide}
          blending={THREE.AdditiveBlending}
        />
      </mesh>
    </group>
  );
}
