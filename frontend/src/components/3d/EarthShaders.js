/**
 * SatQuery AI — Earth Day/Night Shaders
 * 
 * Provides custom GLSL shaders for physically-based day/night blending,
 * solar terminator twilight glow, specular ocean reflection, city lights emission,
 * and dynamic atmospheric Rayleigh scattering.
 */

import * as THREE from 'three';

// ─── Earth Day / Night Surface Shader ───────────────────────────────────────

export const EarthDayNightShader = {
  uniforms: {
    uDayMap: { value: null },
    uNightMap: { value: null },
    uSpecularMap: { value: null },
    uBumpMap: { value: null },
    uSunPosition: { value: new THREE.Vector3(30, 0, 0) },
    uNightLightsBoost: { value: 1.8 },
  },
  vertexShader: `
    varying vec2 vUv;
    varying vec3 vNormal;
    varying vec3 vWorldPosition;

    void main() {
      vUv = uv;
      vec4 worldPos = modelMatrix * vec4(position, 1.0);
      vWorldPosition = worldPos.xyz;
      vNormal = normalize(mat3(modelMatrix) * normal);
      gl_Position = projectionMatrix * viewMatrix * worldPos;
    }
  `,
  fragmentShader: `
    uniform sampler2D uDayMap;
    uniform sampler2D uNightMap;
    uniform sampler2D uSpecularMap;
    uniform vec3 uSunPosition;
    uniform float uNightLightsBoost;

    varying vec2 vUv;
    varying vec3 vNormal;
    varying vec3 vWorldPosition;

    void main() {
      vec3 normal = normalize(vNormal);
      vec3 sunDir = normalize(uSunPosition - vWorldPosition);
      vec3 viewDir = normalize(cameraPosition - vWorldPosition);

      // Dot product between surface normal and sun direction
      float sunDotNormal = dot(normal, sunDir);

      // Smooth day/night terminator transition (-0.12 to +0.12)
      float dayFactor = smoothstep(-0.12, 0.12, sunDotNormal);
      float nightFactor = 1.0 - dayFactor;

      // Textures
      vec3 dayColor = texture2D(uDayMap, vUv).rgb;
      vec3 nightColor = texture2D(uNightMap, vUv).rgb;
      float specularMask = texture2D(uSpecularMap, vUv).r;

      // 1. Direct Sun illumination on day side
      float diffuse = max(sunDotNormal, 0.0);
      vec3 dayLit = dayColor * (diffuse * 0.92 + 0.14);

      // 2. Specular reflection (ocean glint) where water reflects sunlight
      vec3 halfVector = normalize(sunDir + viewDir);
      float specFactor = pow(max(dot(normal, halfVector), 0.0), 38.0) * specularMask * dayFactor;
      vec3 specularColor = vec3(0.92, 0.96, 1.0) * specFactor * 0.8;

      // 3. Twilight golden-amber glow along the terminator line (sunset/sunrise)
      float twilight = (1.0 - abs(sunDotNormal * 8.0)) * step(abs(sunDotNormal), 0.125);
      vec3 twilightGlow = vec3(0.98, 0.44, 0.16) * max(twilight, 0.0) * 0.38;

      // 4. Night city lights (boosted on the dark hemisphere)
      vec3 nightLights = nightColor * nightFactor * uNightLightsBoost;

      // 5. Night ambient starlight (subtle deep blue so dark continents remain visible)
      vec3 nightAmbient = dayColor * 0.038 * nightFactor;

      // Combine surface components
      vec3 finalColor = dayLit + nightLights + nightAmbient + twilightGlow + specularColor;

      // 6. Atmospheric horizon scattering (blue haze around outer rim in sunlight)
      float fresnel = 1.0 - max(dot(viewDir, normal), 0.0);
      float atmosphereLimb = pow(fresnel, 3.2) * (dayFactor * 0.45 + 0.04);
      finalColor += vec3(0.2, 0.6, 1.0) * atmosphereLimb;

      gl_FragColor = vec4(finalColor, 1.0);
    }
  `,
};

// ─── Cloud Layer Shader ───────────────────────────────────────────────────

export const EarthCloudsShader = {
  uniforms: {
    uCloudsMap: { value: null },
    uSunPosition: { value: new THREE.Vector3(30, 0, 0) },
  },
  vertexShader: `
    varying vec2 vUv;
    varying vec3 vNormal;
    varying vec3 vWorldPosition;

    void main() {
      vUv = uv;
      vec4 worldPos = modelMatrix * vec4(position, 1.0);
      vWorldPosition = worldPos.xyz;
      vNormal = normalize(mat3(modelMatrix) * normal);
      gl_Position = projectionMatrix * viewMatrix * worldPos;
    }
  `,
  fragmentShader: `
    uniform sampler2D uCloudsMap;
    uniform vec3 uSunPosition;

    varying vec2 vUv;
    varying vec3 vNormal;
    varying vec3 vWorldPosition;

    void main() {
      vec4 cloud = texture2D(uCloudsMap, vUv);
      vec3 normal = normalize(vNormal);
      vec3 sunDir = normalize(uSunPosition - vWorldPosition);

      float sunDotNormal = dot(normal, sunDir);
      float dayFactor = smoothstep(-0.15, 0.15, sunDotNormal);

      // Day clouds are brilliant white; night clouds are dark silhouettes
      vec3 cloudColor = mix(vec3(0.04, 0.06, 0.12), vec3(1.0, 1.0, 1.0), dayFactor);

      // Sunset tint on clouds along the terminator
      float twilight = (1.0 - abs(sunDotNormal * 7.0)) * step(abs(sunDotNormal), 0.14);
      cloudColor += vec3(0.95, 0.42, 0.18) * max(twilight, 0.0) * 0.55;

      gl_FragColor = vec4(cloudColor, cloud.a * (dayFactor * 0.38 + 0.18));
    }
  `,
};

// ─── Dynamic Atmosphere Rayleigh Scattering Shader ────────────────────────

export const AtmosphereShader = {
  uniforms: {
    uSunPosition: { value: new THREE.Vector3(30, 0, 0) },
  },
  vertexShader: `
    varying vec3 vNormal;
    varying vec3 vWorldPosition;

    void main() {
      vNormal = normalize(normalMatrix * normal);
      vec4 worldPos = modelMatrix * vec4(position, 1.0);
      vWorldPosition = worldPos.xyz;
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    }
  `,
  fragmentShader: `
    uniform vec3 uSunPosition;

    varying vec3 vNormal;
    varying vec3 vWorldPosition;

    void main() {
      vec3 normal = normalize(vNormal);
      vec3 sunDir = normalize(uSunPosition - vWorldPosition);

      float sunDot = dot(normal, sunDir);
      float dayFactor = smoothstep(-0.2, 0.2, sunDot);

      // Fresnel rim glow
      float intensity = pow(0.72 - dot(normal, vec3(0.0, 0.0, 1.0)), 2.2);

      vec3 dayAtmosphere = vec3(0.3, 0.65, 1.0);
      vec3 twilightAtmosphere = vec3(0.96, 0.48, 0.2);
      vec3 nightAtmosphere = vec3(0.04, 0.1, 0.22);

      float twilightFactor = (1.0 - abs(sunDot * 6.0)) * step(abs(sunDot), 0.16);

      vec3 atmosphereColor = mix(nightAtmosphere, dayAtmosphere, dayFactor);
      atmosphereColor += twilightAtmosphere * max(twilightFactor, 0.0) * 0.75;

      gl_FragColor = vec4(atmosphereColor, intensity * (dayFactor * 0.62 + 0.16));
    }
  `,
};
