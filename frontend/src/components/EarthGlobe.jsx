import { useRef, useMemo, useEffect, useCallback, Component, Suspense } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { OrbitControls, Stars, useTexture, Html } from '@react-three/drei';
import * as THREE from 'three';
import { useAppStore } from '../store/useAppStore';
import { latLngToVector3, altitudeToDistance } from '../hooks/useGlobeControls';
import { formatAltitude } from '../services/api';

const GLOBE_RADIUS = 2;

// Local high-resolution Blue Marble textures (offline & CORS safe)
const BASE_URL = import.meta.env.BASE_URL || '/';
const getTexturePath = (path) => `${BASE_URL.replace(/\/$/, '')}/${path.replace(/^\//, '')}`;

const EARTH_TEXTURE = getTexturePath('textures/earth-blue-marble.jpg');
const EARTH_BUMP = getTexturePath('textures/earth-topology.png');
const EARTH_SPECULAR = getTexturePath('textures/earth-water.png');
const EARTH_NIGHT = getTexturePath('textures/earth-night.jpg');
const EARTH_CLOUDS = getTexturePath('textures/earth-clouds.png');

// ─── Atmosphere Shader ──────────────────────────────────

const AtmosphereShader = {
  vertexShader: `
    varying vec3 vNormal;
    varying vec3 vPosition;
    void main() {
      vNormal = normalize(normalMatrix * normal);
      vPosition = (modelViewMatrix * vec4(position, 1.0)).xyz;
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    }
  `,
  fragmentShader: `
    varying vec3 vNormal;
    varying vec3 vPosition;
    void main() {
      float intensity = pow(0.72 - dot(vNormal, vec3(0.0, 0.0, 1.0)), 2.2);
      vec3 atmosphere = vec3(0.3, 0.6, 1.0) * intensity;
      float alpha = intensity * 0.65;
      gl_FragColor = vec4(atmosphere, alpha);
    }
  `,
};

// ─── Procedural Fallback Earth (instant load / texture fault recovery) ───

function ProceduralEarth() {
  const meshRef = useRef();

  useFrame((_, delta) => {
    if (meshRef.current) {
      meshRef.current.rotation.y += delta * 0.03;
    }
  });

  return (
    <group>
      {/* Base Earth Sphere with high-contrast ocean & land gradient */}
      <mesh ref={meshRef}>
        <sphereGeometry args={[GLOBE_RADIUS, 64, 64]} />
        <meshPhongMaterial
          color="#0d2b45"
          emissive="#021020"
          specular={new THREE.Color(0x38bdf8)}
          shininess={30}
        />
      </mesh>

      {/* Lat/Long Coordinate Grid Wireframe */}
      <mesh scale={[1.002, 1.002, 1.002]}>
        <sphereGeometry args={[GLOBE_RADIUS, 36, 18]} />
        <meshBasicMaterial
          color="#38bdf8"
          wireframe
          transparent
          opacity={0.18}
        />
      </mesh>

      {/* Atmosphere Glow */}
      <mesh scale={[1.14, 1.14, 1.14]}>
        <sphereGeometry args={[GLOBE_RADIUS, 64, 64]} />
        <shaderMaterial
          vertexShader={AtmosphereShader.vertexShader}
          fragmentShader={AtmosphereShader.fragmentShader}
          side={THREE.BackSide}
          transparent
          depthWrite={false}
        />
      </mesh>
    </group>
  );
}

// ─── Fiber-level Error Boundary for 3D Mesh ─────────────

class EarthMeshErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(err) {
    console.warn('[EarthMeshErrorBoundary] Textures failed to mount, using procedural earth:', err);
  }

  render() {
    if (this.state.hasError) {
      return <ProceduralEarth />;
    }
    return this.props.children;
  }
}

// ─── Earth Sphere with Real Textures ────────────────────

function Earth() {
  const meshRef = useRef();
  const cloudsRef = useRef();
  const [dayTexture, bumpTexture, specularTexture, nightTexture, cloudsTexture] = useTexture([
    EARTH_TEXTURE,
    EARTH_BUMP,
    EARTH_SPECULAR,
    EARTH_NIGHT,
    EARTH_CLOUDS,
  ]);

  useFrame((_, delta) => {
    if (cloudsRef.current) {
      cloudsRef.current.rotation.y += delta * 0.008;
    }
  });

  return (
    <group>
      {/* Main Earth */}
      <mesh ref={meshRef}>
        <sphereGeometry args={[GLOBE_RADIUS, 64, 64]} />
        <meshPhongMaterial
          map={dayTexture}
          bumpMap={bumpTexture}
          bumpScale={0.04}
          specularMap={specularTexture}
          specular={new THREE.Color(0x333333)}
          shininess={15}
        />
      </mesh>

      {/* Night Lights Layer */}
      <mesh>
        <sphereGeometry args={[GLOBE_RADIUS + 0.001, 64, 64]} />
        <meshBasicMaterial
          map={nightTexture}
          transparent
          opacity={0.4}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
        />
      </mesh>

      {/* Clouds Layer */}
      <mesh ref={cloudsRef}>
        <sphereGeometry args={[GLOBE_RADIUS + 0.015, 64, 64]} />
        <meshPhongMaterial
          map={cloudsTexture}
          transparent
          opacity={0.25}
          depthWrite={false}
        />
      </mesh>

      {/* Atmosphere Glow */}
      <mesh scale={[1.14, 1.14, 1.14]}>
        <sphereGeometry args={[GLOBE_RADIUS, 64, 64]} />
        <shaderMaterial
          vertexShader={AtmosphereShader.vertexShader}
          fragmentShader={AtmosphereShader.fragmentShader}
          side={THREE.BackSide}
          transparent
          depthWrite={false}
        />
      </mesh>
    </group>
  );
}

// ─── Location Marker ────────────────────────────────────

function LocationMarker({ lat, lng, label, color = '#facc15', pulse = true }) {
  const position = useMemo(
    () => latLngToVector3(lat, lng, GLOBE_RADIUS + 0.02),
    [lat, lng]
  );
  const markerRef = useRef();

  useFrame(() => {
    if (pulse && markerRef.current) {
      const time = performance.now() * 0.001;
      const scale = 1 + Math.sin(time * 3) * 0.3;
      markerRef.current.scale.setScalar(scale);
    }
  });

  return (
    <group position={position}>
      {/* Marker Point */}
      <mesh ref={markerRef}>
        <sphereGeometry args={[0.02, 16, 16]} />
        <meshBasicMaterial color={color} />
      </mesh>
      {/* Glow Ring */}
      <mesh rotation={[Math.PI / 2, 0, 0]}>
        <ringGeometry args={[0.03, 0.045, 32]} />
        <meshBasicMaterial color={color} transparent opacity={0.5} side={THREE.DoubleSide} />
      </mesh>
      {/* Label */}
      {label && (
        <Html
          position={[0, 0.08, 0]}
          center
          style={{
            whiteSpace: 'nowrap',
            pointerEvents: 'none',
            userSelect: 'none',
          }}
        >
          <div className="px-2 py-0.5 rounded text-[9px] font-mono text-emerald-light bg-bg-deep/85 border border-border whitespace-nowrap">
            {label}
          </div>
        </Html>
      )}
    </group>
  );
}

// ─── Analysis Entity on Globe ───────────────────────────

function AnalysisMarker({ lat, lng, label, color = '#38bdf8' }) {
  const position = useMemo(
    () => latLngToVector3(lat, lng, GLOBE_RADIUS + 0.015),
    [lat, lng]
  );
  const ringRef = useRef();

  useFrame(() => {
    if (ringRef.current) {
      const time = performance.now() * 0.001;
      ringRef.current.rotation.z = time * 1.5;
    }
  });

  return (
    <group position={position}>
      <mesh>
        <sphereGeometry args={[0.015, 12, 12]} />
        <meshBasicMaterial color={color} transparent opacity={0.8} />
      </mesh>
      <mesh ref={ringRef} rotation={[Math.PI / 2, 0, 0]}>
        <ringGeometry args={[0.025, 0.035, 4]} />
        <meshBasicMaterial color={color} transparent opacity={0.6} side={THREE.DoubleSide} />
      </mesh>
      {label && (
        <Html position={[0, 0.06, 0]} center style={{ pointerEvents: 'none' }}>
          <div className="px-1.5 py-0.5 rounded text-[8px] font-mono whitespace-nowrap border border-border"
            style={{ color, background: 'rgba(7,17,30,0.85)' }}>
            {label}
          </div>
        </Html>
      )}
    </group>
  );
}

// ─── Camera Controller ──────────────────────────────────

function CameraController() {
  const { camera } = useThree();
  const { state, actions } = useAppStore();
  const controlsRef = useRef();
  const animatingRef = useRef(false);

  // Handle fly-to events
  useEffect(() => {
    if (!state.flyToTarget) return;

    const { latitude, longitude, altitude } = state.flyToTarget;
    const targetPos = latLngToVector3(latitude, longitude, GLOBE_RADIUS);
    const distance = altitudeToDistance(altitude);
    const normal = targetPos.clone().normalize();
    const targetCameraPos = normal.multiplyScalar(distance);

    const startPos = camera.position.clone();
    const startTime = Date.now();
    const duration = 2400;
    animatingRef.current = true;

    function animate() {
      const elapsed = Date.now() - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased = progress < 0.5
        ? 4 * progress * progress * progress
        : 1 - Math.pow(-2 * progress + 2, 3) / 2;

      camera.position.lerpVectors(startPos, targetCameraPos, eased);
      camera.lookAt(0, 0, 0);

      if (controlsRef.current) {
        controlsRef.current.target.set(0, 0, 0);
        controlsRef.current.update();
      }

      if (progress < 1) {
        requestAnimationFrame(animate);
      } else {
        animatingRef.current = false;
        actions.clearFlyTarget();
      }
    }
    animate();
  }, [state.flyToTarget, camera, actions]);

  // Update telemetry from camera
  useFrame(() => {
    if (animatingRef.current) return;
    const pos = camera.position.clone();
    const distance = pos.length();
    const altitudeKm = (distance / GLOBE_RADIUS) * 6371 - 6371;
    const altitudeM = Math.max(0, altitudeKm * 1000);

    const direction = pos.normalize();
    const lat = 90 - (Math.acos(direction.y) * 180 / Math.PI);
    const lng = ((Math.atan2(direction.z, -direction.x) * 180 / Math.PI) - 180 + 540) % 360 - 180;

    actions.updateTelemetry(
      formatAltitude(altitudeM),
      `${lat.toFixed(3)}°, ${lng.toFixed(3)}°`
    );
  });

  return (
    <OrbitControls
      ref={controlsRef}
      enablePan={false}
      minDistance={GLOBE_RADIUS + 0.2}
      maxDistance={20}
      enableDamping
      dampingFactor={0.08}
      rotateSpeed={0.5}
      zoomSpeed={0.8}
    />
  );
}

// ─── Scene Lights ───────────────────────────────────────

function SceneLights() {
  return (
    <>
      <ambientLight intensity={0.15} />
      <directionalLight
        position={[5, 3, 5]}
        intensity={1.8}
        color="#ffffff"
      />
      <directionalLight
        position={[-3, -1, -4]}
        intensity={0.2}
        color="#4488ff"
      />
    </>
  );
}

// ─── Main Globe Component ───────────────────────────────

export default function EarthGlobe() {
  const { state } = useAppStore();

  return (
    <div className="earth-canvas w-full h-full bg-bg-deep">
      <Canvas
        camera={{
          position: [0, 0, 6],
          fov: 45,
          near: 0.1,
          far: 100,
        }}
        gl={{
          antialias: true,
          alpha: false,
          powerPreference: 'high-performance',
        }}
        onCreated={({ gl }) => {
          gl.domElement?.addEventListener('webglcontextlost', (event) => {
            event.preventDefault();
            console.warn('[EarthGlobe] WebGL context lost. Preventing crash...');
          });
        }}
        style={{ background: '#06101b' }}
      >
        <SceneLights />
        <Stars
          radius={50}
          depth={50}
          count={5000}
          factor={4}
          saturation={0}
          fade
          speed={0.5}
        />
        
        {/* Safe fallback for Earth mesh if textures delay or encounter issues */}
        <Suspense fallback={<ProceduralEarth />}>
          <EarthMeshErrorBoundary>
            <Earth />
          </EarthMeshErrorBoundary>
        </Suspense>

        <CameraController />

        {/* Active location marker */}
        {state.locationLabel && (
          <LocationMarker
            lat={state.activeLocation.latitude}
            lng={state.activeLocation.longitude}
            label={state.locationLabel}
            color="#10b981"
          />
        )}

        {/* Analysis entities */}
        {state.analysisEntities.map((entity, i) => (
          <AnalysisMarker
            key={`entity-${i}`}
            lat={entity.lat}
            lng={entity.lng}
            label={entity.label}
            color={entity.color || '#facc15'}
          />
        ))}
      </Canvas>
    </div>
  );
}
