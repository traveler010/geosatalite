import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import { Stars, Html } from '@react-three/drei';
import * as THREE from 'three';

// ─── 1. The Sun with Corona Glow & Directional Illumination ───────────────────

export function Sun({ sunPosition }) {
  const coronaRef = useRef();

  useFrame((_, delta) => {
    if (coronaRef.current) {
      coronaRef.current.rotation.z += delta * 0.05;
    }
  });

  return (
    <group position={sunPosition}>
      {/* Primary Directional Light casting solar light onto Earth and Moon */}
      <directionalLight
        position={[0, 0, 0]}
        intensity={2.6}
        color="#fffbf2"
        castShadow={false}
      />

      {/* Radiant Sun Core */}
      <mesh>
        <sphereGeometry args={[1.5, 32, 32]} />
        <meshBasicMaterial color="#ffffff" />
      </mesh>

      {/* Solar Atmosphere Inner Halo */}
      <mesh scale={[1.25, 1.25, 1.25]}>
        <sphereGeometry args={[1.5, 32, 32]} />
        <meshBasicMaterial
          color="#fde047"
          transparent
          opacity={0.7}
          blending={THREE.AdditiveBlending}
        />
      </mesh>

      {/* Solar Corona Outer Flare */}
      <mesh ref={coronaRef} scale={[2.6, 2.6, 2.6]}>
        <sphereGeometry args={[1.5, 32, 32]} />
        <meshBasicMaterial
          color="#f97316"
          transparent
          opacity={0.25}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
        />
      </mesh>

      {/* Distant Sun Flare Ring */}
      <mesh scale={[4.2, 4.2, 4.2]}>
        <ringGeometry args={[1.5, 1.9, 64]} />
        <meshBasicMaterial
          color="#facc15"
          transparent
          opacity={0.15}
          side={THREE.DoubleSide}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
        />
      </mesh>
    </group>
  );
}

// ─── 2. The Moon with Natural Phases ──────────────────────────────────────────

export function Moon({ moonPosition, sunPosition }) {
  const moonRef = useRef();

  useFrame((_, delta) => {
    if (moonRef.current) {
      moonRef.current.rotation.y += delta * 0.01;
    }
  });

  return (
    <group position={moonPosition}>
      <mesh ref={moonRef}>
        <sphereGeometry args={[0.54, 32, 32]} />
        <meshStandardMaterial
          color="#c8cdd4"
          roughness={0.88}
          metalness={0.05}
          bumpScale={0.05}
        />
      </mesh>

      {/* Moon Label on Orbit */}
      <Html position={[0, 0.75, 0]} center style={{ pointerEvents: 'none' }}>
        <div className="px-1.5 py-0.5 rounded text-[8px] font-mono whitespace-nowrap bg-bg-deep/80 text-muted border border-border">
          MOON (Natural Satellite)
        </div>
      </Html>
    </group>
  );
}

// ─── 3. Deep Cosmic Nebula & Celestial Dust ───────────────────────────────────

export function CosmicNebula() {
  const nebulaPoints = useMemo(() => {
    const count = 1400;
    const positions = new Float32Array(count * 3);
    const colors = new Float32Array(count * 3);

    const palette = [
      new THREE.Color('#38bdf8'), // Cyan
      new THREE.Color('#818cf8'), // Indigo
      new THREE.Color('#c084fc'), // Purple
      new THREE.Color('#f43f5e'), // Magenta/Rose
      new THREE.Color('#06b6d4'), // Deep cyan
    ];

    for (let i = 0; i < count; i++) {
      // Create a galactic disc distribution
      const theta = Math.random() * Math.PI * 2;
      const radius = 35 + Math.random() * 45;
      const height = (Math.random() - 0.5) * 16;

      positions[i * 3] = radius * Math.cos(theta);
      positions[i * 3 + 1] = height;
      positions[i * 3 + 2] = radius * Math.sin(theta);

      const color = palette[Math.floor(Math.random() * palette.length)];
      colors[i * 3] = color.r;
      colors[i * 3 + 1] = color.g;
      colors[i * 3 + 2] = color.b;
    }

    return { positions, colors };
  }, []);

  const pointsRef = useRef();
  useFrame((_, delta) => {
    if (pointsRef.current) {
      pointsRef.current.rotation.y += delta * 0.001;
    }
  });

  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          args={[nebulaPoints.positions, 3]}
        />
        <bufferAttribute
          attach="attributes-color"
          args={[nebulaPoints.colors, 3]}
        />
      </bufferGeometry>
      <pointsMaterial
        size={0.65}
        vertexColors
        transparent
        opacity={0.35}
        blending={THREE.AdditiveBlending}
        depthWrite={false}
      />
    </points>
  );
}

// ─── 4. Remote Sensing Orbital Satellites ─────────────────────────────────────

export function OrbitalSatellites({ globeRadius = 2.0 }) {
  const sat1Ref = useRef();
  const sat2Ref = useRef();
  const sat3Ref = useRef();

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();

    // Sat 1: Cartosat-3 (Polar Sun-synchronous orbit, radius 2.38)
    if (sat1Ref.current) {
      const r1 = globeRadius + 0.38;
      const angle1 = t * 0.45;
      sat1Ref.current.position.set(
        r1 * Math.cos(angle1) * 0.15,
        r1 * Math.sin(angle1),
        r1 * Math.cos(angle1) * 0.98
      );
    }

    // Sat 2: RISAT-SAR (Inclined orbit ~45°, radius 2.52)
    if (sat2Ref.current) {
      const r2 = globeRadius + 0.52;
      const angle2 = t * 0.35 + 2.0;
      sat2Ref.current.position.set(
        r2 * Math.cos(angle2),
        r2 * Math.sin(angle2) * 0.7,
        r2 * Math.sin(angle2) * 0.7
      );
    }

    // Sat 3: Oceansat / Earth Observation (Equatorial/retrograde, radius 2.7)
    if (sat3Ref.current) {
      const r3 = globeRadius + 0.7;
      const angle3 = t * 0.25 + 4.2;
      sat3Ref.current.position.set(
        r3 * Math.cos(angle3),
        r3 * Math.sin(angle3) * 0.2,
        r3 * Math.sin(angle3)
      );
    }
  });

  return (
    <group>
      {/* Orbital Path 1 Ring */}
      <mesh rotation={[Math.PI / 2.3, 0.2, 0]}>
        <ringGeometry args={[globeRadius + 0.375, globeRadius + 0.385, 96]} />
        <meshBasicMaterial color="#38bdf8" transparent opacity={0.18} side={THREE.DoubleSide} />
      </mesh>

      {/* Orbital Path 2 Ring */}
      <mesh rotation={[Math.PI / 3.8, -0.4, 0.3]}>
        <ringGeometry args={[globeRadius + 0.515, globeRadius + 0.525, 96]} />
        <meshBasicMaterial color="#10b981" transparent opacity={0.18} side={THREE.DoubleSide} />
      </mesh>

      {/* Satellite 1: Cartosat-3 */}
      <group ref={sat1Ref}>
        {/* Central Satellite Body */}
        <mesh>
          <boxGeometry args={[0.035, 0.035, 0.05]} />
          <meshStandardMaterial color="#f59e0b" roughness={0.3} metalness={0.9} />
        </mesh>
        {/* Left Solar Panel */}
        <mesh position={[-0.055, 0, 0]}>
          <boxGeometry args={[0.065, 0.025, 0.003]} />
          <meshStandardMaterial color="#1d4ed8" roughness={0.2} metalness={0.7} />
        </mesh>
        {/* Right Solar Panel */}
        <mesh position={[0.055, 0, 0]}>
          <boxGeometry args={[0.065, 0.025, 0.003]} />
          <meshStandardMaterial color="#1d4ed8" roughness={0.2} metalness={0.7} />
        </mesh>
        <Html position={[0, 0.06, 0]} center style={{ pointerEvents: 'none' }}>
          <div className="px-1 py-0.2 rounded text-[7px] font-mono text-cyan-300 bg-bg-deep/85 border border-cyan-500/30 whitespace-nowrap">
            CARTOSAT-3 (LEO)
          </div>
        </Html>
      </group>

      {/* Satellite 2: RISAT / SAR */}
      <group ref={sat2Ref}>
        <mesh>
          <boxGeometry args={[0.038, 0.038, 0.045]} />
          <meshStandardMaterial color="#94a3b8" roughness={0.2} metalness={0.85} />
        </mesh>
        <mesh position={[-0.06, 0, 0]}>
          <boxGeometry args={[0.07, 0.028, 0.003]} />
          <meshStandardMaterial color="#0284c7" roughness={0.2} metalness={0.8} />
        </mesh>
        <mesh position={[0.06, 0, 0]}>
          <boxGeometry args={[0.07, 0.028, 0.003]} />
          <meshStandardMaterial color="#0284c7" roughness={0.2} metalness={0.8} />
        </mesh>
        <Html position={[0, 0.06, 0]} center style={{ pointerEvents: 'none' }}>
          <div className="px-1 py-0.2 rounded text-[7px] font-mono text-emerald-dim bg-bg-deep/85 border border-emerald/30 whitespace-nowrap">
            EOS-04 / SAR
          </div>
        </Html>
      </group>

      {/* Satellite 3: Oceansat */}
      <group ref={sat3Ref}>
        <mesh>
          <boxGeometry args={[0.03, 0.03, 0.04]} />
          <meshStandardMaterial color="#cbd5e1" roughness={0.3} metalness={0.8} />
        </mesh>
        <mesh position={[-0.05, 0, 0]}>
          <boxGeometry args={[0.055, 0.022, 0.003]} />
          <meshStandardMaterial color="#2563eb" roughness={0.2} metalness={0.7} />
        </mesh>
        <mesh position={[0.05, 0, 0]}>
          <boxGeometry args={[0.055, 0.022, 0.003]} />
          <meshStandardMaterial color="#2563eb" roughness={0.2} metalness={0.7} />
        </mesh>
        <Html position={[0, 0.06, 0]} center style={{ pointerEvents: 'none' }}>
          <div className="px-1 py-0.2 rounded text-[7px] font-mono text-amber-300 bg-bg-deep/85 border border-amber-500/30 whitespace-nowrap">
            OCEANSAT-3
          </div>
        </Html>
      </group>
    </group>
  );
}

// ─── 5. Complete Universe Composite ───────────────────────────────────────────

export function Universe({ sunPosition, moonPosition, globeRadius = 2.0 }) {
  return (
    <group>
      {/* Distant Starfields: Deep Space */}
      <Stars
        radius={70}
        depth={60}
        count={7500}
        factor={4.5}
        saturation={0.4}
        fade
        speed={0.4}
      />

      {/* Galactic Nebula Dust Band */}
      <CosmicNebula />

      {/* The Sun */}
      <Sun sunPosition={sunPosition} />

      {/* The Moon with Phases */}
      <Moon moonPosition={moonPosition} sunPosition={sunPosition} />

      {/* Active Remote Sensing Satellites */}
      <OrbitalSatellites globeRadius={globeRadius} />
    </group>
  );
}
