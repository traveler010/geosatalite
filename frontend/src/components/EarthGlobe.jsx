import { useRef, useMemo, useState, useEffect, Component, Suspense } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { OrbitControls, useTexture, Html } from '@react-three/drei';
import * as THREE from 'three';
import { useAppStore } from '../store/useAppStore';
import { latLngToVector3, altitudeToDistance } from '../hooks/useGlobeControls';
import { formatAltitude } from '../services/api';
import { calculateSolarPosition } from '../utils/solarCalculator';
import { Universe } from './3d/Universe';
import { EarthDayNightShader, EarthCloudsShader, AtmosphereShader } from './3d/EarthShaders';
import TargetReticle from './3d/TargetReticle';

const GLOBE_RADIUS = 2;

// Local high-resolution Blue Marble textures (offline & CORS safe)
const BASE_URL = import.meta.env.BASE_URL || '/';
const getTexturePath = (path) => `${BASE_URL.replace(/\/$/, '')}/${path.replace(/^\//, '')}`;

const EARTH_TEXTURE = getTexturePath('textures/earth-blue-marble.jpg');
const EARTH_BUMP = getTexturePath('textures/earth-topology.png');
const EARTH_SPECULAR = getTexturePath('textures/earth-water.png');
const EARTH_NIGHT = getTexturePath('textures/earth-night.jpg');
const EARTH_CLOUDS = getTexturePath('textures/earth-clouds.png');

// ─── Procedural Fallback Earth (instant load / texture fault recovery) ───

function ProceduralEarth({ sunPosition }) {
  const meshRef = useRef();

  useFrame((_, delta) => {
    if (meshRef.current) {
      meshRef.current.rotation.y += delta * 0.02;
    }
  });

  return (
    <group>
      {/* Base Earth Sphere with ocean & land gradient */}
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
          uniforms={{
            uSunPosition: { value: sunPosition },
          }}
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
      return <ProceduralEarth sunPosition={this.props.sunPosition} />;
    }
    return this.props.children;
  }
}

// ─── Earth Sphere with Dynamic Day/Night Shaders ────────

function Earth({ sunPosition, nightLightsBoost = 1.8 }) {
  const meshRef = useRef();
  const cloudsRef = useRef();
  const atmosphereRef = useRef();

  const [dayTexture, bumpTexture, specularTexture, nightTexture, cloudsTexture] = useTexture([
    EARTH_TEXTURE,
    EARTH_BUMP,
    EARTH_SPECULAR,
    EARTH_NIGHT,
    EARTH_CLOUDS,
  ]);

  // Configure texture wrap and filtering
  useMemo(() => {
    [dayTexture, bumpTexture, specularTexture, nightTexture, cloudsTexture].forEach((tex) => {
      if (tex) {
        tex.wrapS = THREE.RepeatWrapping;
        tex.wrapT = THREE.ClampToEdgeWrapping;
        tex.generateMipmaps = true;
        tex.minFilter = THREE.LinearMipmapLinearFilter;
      }
    });
  }, [dayTexture, bumpTexture, specularTexture, nightTexture, cloudsTexture]);

  // Day/Night surface material uniforms
  const earthUniforms = useMemo(() => ({
    uDayMap: { value: dayTexture },
    uNightMap: { value: nightTexture },
    uSpecularMap: { value: specularTexture },
    uBumpMap: { value: bumpTexture },
    uSunPosition: { value: sunPosition },
    uNightLightsBoost: { value: nightLightsBoost },
  }), [dayTexture, nightTexture, specularTexture, bumpTexture]);

  // Cloud material uniforms
  const cloudsUniforms = useMemo(() => ({
    uCloudsMap: { value: cloudsTexture },
    uSunPosition: { value: sunPosition },
  }), [cloudsTexture]);

  // Atmosphere material uniforms
  const atmosphereUniforms = useMemo(() => ({
    uSunPosition: { value: sunPosition },
  }), []);

  // Update uniforms and dynamic clouds rotation on every frame
  useFrame((_, delta) => {
    if (meshRef.current?.material) {
      meshRef.current.material.uniforms.uSunPosition.value.copy(sunPosition);
      meshRef.current.material.uniforms.uNightLightsBoost.value = nightLightsBoost;
    }
    if (cloudsRef.current) {
      cloudsRef.current.rotation.y += delta * 0.008;
      if (cloudsRef.current.material?.uniforms?.uSunPosition) {
        cloudsRef.current.material.uniforms.uSunPosition.value.copy(sunPosition);
      }
    }
    if (atmosphereRef.current?.material?.uniforms?.uSunPosition) {
      atmosphereRef.current.material.uniforms.uSunPosition.value.copy(sunPosition);
    }
  });

  return (
    <group>
      {/* Main Earth Sphere with Day/Night GLSL blending */}
      <mesh ref={meshRef}>
        <sphereGeometry args={[GLOBE_RADIUS, 64, 64]} />
        <shaderMaterial
          vertexShader={EarthDayNightShader.vertexShader}
          fragmentShader={EarthDayNightShader.fragmentShader}
          uniforms={earthUniforms}
        />
      </mesh>

      {/* Rotating Dynamic Clouds with Day/Night Lighting & Twilight Tint */}
      <mesh ref={cloudsRef}>
        <sphereGeometry args={[GLOBE_RADIUS + 0.016, 64, 64]} />
        <shaderMaterial
          vertexShader={EarthCloudsShader.vertexShader}
          fragmentShader={EarthCloudsShader.fragmentShader}
          uniforms={cloudsUniforms}
          transparent
          depthWrite={false}
        />
      </mesh>

      {/* Atmospheric Rayleigh Scattering Shell */}
      <mesh ref={atmosphereRef} scale={[1.14, 1.14, 1.14]}>
        <sphereGeometry args={[GLOBE_RADIUS, 64, 64]} />
        <shaderMaterial
          vertexShader={AtmosphereShader.vertexShader}
          fragmentShader={AtmosphereShader.fragmentShader}
          uniforms={atmosphereUniforms}
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
          <div className="px-2 py-0.5 rounded text-[9px] font-mono text-emerald-light bg-bg-deep/85 border border-border whitespace-nowrap shadow-lg">
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
          <div className="px-1.5 py-0.5 rounded text-[8px] font-mono whitespace-nowrap border border-border shadow-md"
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
      maxDistance={25}
      enableDamping
      dampingFactor={0.08}
      rotateSpeed={0.5}
      zoomSpeed={0.8}
    />
  );
}

// ─── Main Globe Component with Universe & Solar Simulator ──

export default function EarthGlobe() {
  const { state } = useAppStore();
  const [liveDate, setLiveDate] = useState(new Date());

  // Continuously advance live time
  useEffect(() => {
    const timer = setInterval(() => {
      setLiveDate(new Date());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // Compute effective date based on timeMode
  const effectiveDate = useMemo(() => {
    if (state.timeMode === 'live') {
      return liveDate;
    }
    const d = new Date(liveDate);
    const totalMinutes = state.customUtcHours * 60;
    const hours = Math.floor(totalMinutes / 60) % 24;
    const minutes = Math.floor(totalMinutes % 60);
    const seconds = Math.floor((totalMinutes * 60) % 60);
    d.setUTCHours(hours, minutes, seconds, 0);
    return d;
  }, [state.timeMode, liveDate, state.customUtcHours]);

  // Solar position in Universe space
  const solar = useMemo(() => {
    return calculateSolarPosition(effectiveDate);
  }, [effectiveDate]);

  return (
    <div className="earth-canvas w-full h-full bg-bg-deep relative">
      <Canvas
        camera={{
          position: [0, 0, 6],
          fov: 45,
          near: 0.1,
          far: 200,
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
        style={{ background: '#040813' }}
      >
        {/* Subtle deep ambient space illumination */}
        <ambientLight intensity={0.08} />

        {/* 3D Universe: Sun, Moon, Nebula Band, Stars & Orbital Satellites */}
        <Universe
          sunPosition={solar.sunPosition}
          moonPosition={solar.moonPosition}
          globeRadius={GLOBE_RADIUS}
        />

        {/* 3D Earth with Dynamic Day/Night Lighting */}
        <Suspense fallback={<ProceduralEarth sunPosition={solar.sunPosition} />}>
          <EarthMeshErrorBoundary sunPosition={solar.sunPosition}>
            <Earth
              sunPosition={solar.sunPosition}
              nightLightsBoost={state.nightLightsBoost}
            />
          </EarthMeshErrorBoundary>
        </Suspense>

        <CameraController />

        {/* Active location marker & Holographic Reticle */}
        {state.locationLabel && (
          <>
            <TargetReticle
              lat={state.activeLocation.latitude}
              lng={state.activeLocation.longitude}
              globeState={state.globeState}
            />
            <LocationMarker
              lat={state.activeLocation.latitude}
              lng={state.activeLocation.longitude}
              label={state.locationLabel}
              color="#10b981"
            />
          </>
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
