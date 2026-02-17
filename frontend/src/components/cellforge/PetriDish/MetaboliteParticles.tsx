import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import { useCellForgeStore } from '@/stores/cellforgeStore';
import * as THREE from 'three';
import type { Points, BufferAttribute } from 'three';

const COUNT = 120;
const BOUNDS = 4.5;

interface ParticleState {
  x: Float32Array;
  z: Float32Array;
  y: Float32Array;
  vx: Float32Array;
  vz: Float32Array;
  type: Uint8Array;
  phase: Float32Array;
}

function createSpriteTexture(): THREE.Texture {
  const size = 64;
  const canvas = document.createElement('canvas');
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext('2d')!;
  const g = ctx.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
  g.addColorStop(0, 'rgba(255,255,255,1)');
  g.addColorStop(0.15, 'rgba(255,255,255,0.8)');
  g.addColorStop(0.4, 'rgba(255,255,255,0.3)');
  g.addColorStop(0.7, 'rgba(255,255,255,0.05)');
  g.addColorStop(1, 'rgba(255,255,255,0)');
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, size, size);
  const tex = new THREE.CanvasTexture(canvas);
  tex.needsUpdate = true;
  return tex;
}

const TYPE_COLORS: [number, number, number][] = [
  [0.15, 0.35, 0.6],
  [0.6, 0.35, 0.1],
  [0.15, 0.5, 0.25],
];

// Custom shader that actually reads per-point size attribute
const pointsVert = /* glsl */ `
  attribute float size;
  varying vec3 vColor;
  void main() {
    vColor = color;
    vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
    gl_PointSize = size * (200.0 / -mvPosition.z);
    gl_Position = projectionMatrix * mvPosition;
  }
`;

const pointsFrag = /* glsl */ `
  uniform sampler2D uSprite;
  varying vec3 vColor;
  void main() {
    vec4 tex = texture2D(uSprite, gl_PointCoord);
    if (tex.a < 0.01) discard;
    gl_FragColor = vec4(vColor * tex.rgb, tex.a * 0.45);
  }
`;

export function MetaboliteParticles() {
  const pointsRef = useRef<Points>(null);
  const state = useCellForgeStore((s) => s.state);

  const spriteTex = useMemo(createSpriteTexture, []);

  const uniforms = useMemo(() => ({
    uSprite: { value: spriteTex },
  }), [spriteTex]);

  const { particles, positions, colors, sizes } = useMemo(() => {
    const ps: ParticleState = {
      x: new Float32Array(COUNT),
      z: new Float32Array(COUNT),
      y: new Float32Array(COUNT),
      vx: new Float32Array(COUNT),
      vz: new Float32Array(COUNT),
      type: new Uint8Array(COUNT),
      phase: new Float32Array(COUNT),
    };
    const pos = new Float32Array(COUNT * 3);
    const col = new Float32Array(COUNT * 3);
    const sz = new Float32Array(COUNT);

    for (let i = 0; i < COUNT; i++) {
      const angle = Math.random() * Math.PI * 2;
      const dist = 1.2 + Math.random() * 3.3;
      ps.x[i] = Math.cos(angle) * dist;
      ps.z[i] = Math.sin(angle) * dist;
      ps.y[i] = -0.15 + Math.random() * 0.6;
      ps.vx[i] = (Math.random() - 0.5) * 0.008;
      ps.vz[i] = (Math.random() - 0.5) * 0.008;
      ps.type[i] = (i % 3) as 0 | 1 | 2;
      ps.phase[i] = Math.random() * Math.PI * 2;

      const c = TYPE_COLORS[ps.type[i]];
      col[i * 3] = c[0];
      col[i * 3 + 1] = c[1];
      col[i * 3 + 2] = c[2];
      sz[i] = 8;
    }

    return { particles: ps, positions: pos, colors: col, sizes: sz };
  }, []);

  useFrame(() => {
    const pts = pointsRef.current;
    if (!pts) return;

    const glucose = state.metaboliteConcentrations.glucose ?? 10;
    const atpVal = state.metaboliteConcentrations.atp ?? 5;
    const scales = [
      Math.min(1, glucose / 12),
      Math.min(1, atpVal / 8),
      0.6,
    ];
    const t = performance.now() * 0.001;
    const p = particles;

    for (let i = 0; i < COUNT; i++) {
      p.x[i] += p.vx[i];
      p.z[i] += p.vz[i];
      p.vx[i] += (Math.random() - 0.5) * 0.004;
      p.vz[i] += (Math.random() - 0.5) * 0.004;
      p.vx[i] *= 0.975;
      p.vz[i] *= 0.975;
      p.vx[i] -= p.x[i] * 0.001;
      p.vz[i] -= p.z[i] * 0.001;

      if (Math.abs(p.x[i]) > BOUNDS) p.vx[i] -= Math.sign(p.x[i]) * 0.006;
      if (Math.abs(p.z[i]) > BOUNDS) p.vz[i] -= Math.sign(p.z[i]) * 0.006;

      const y = p.y[i] + Math.sin(t * 1.0 + p.phase[i]) * 0.1;

      positions[i * 3] = p.x[i];
      positions[i * 3 + 1] = y;
      positions[i * 3 + 2] = p.z[i];

      const conc = scales[p.type[i]];
      sizes[i] = 4 + conc * 12;

      const c = TYPE_COLORS[p.type[i]];
      const bright = 0.35 + conc * 0.65;
      colors[i * 3] = c[0] * bright;
      colors[i * 3 + 1] = c[1] * bright;
      colors[i * 3 + 2] = c[2] * bright;
    }

    const geom = pts.geometry;
    (geom.attributes.position as BufferAttribute).needsUpdate = true;
    (geom.attributes.color as BufferAttribute).needsUpdate = true;
    (geom.attributes.size as BufferAttribute).needsUpdate = true;
  });

  return (
    <points ref={pointsRef} frustumCulled={false}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
        <bufferAttribute attach="attributes-color" args={[colors, 3]} />
        <bufferAttribute attach="attributes-size" args={[sizes, 1]} />
      </bufferGeometry>
      <shaderMaterial
        vertexShader={pointsVert}
        fragmentShader={pointsFrag}
        uniforms={uniforms}
        vertexColors
        transparent
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </points>
  );
}
