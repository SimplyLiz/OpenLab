import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import { useCellForgeStore } from '@/stores/cellforgeStore';
import type { Mesh, InstancedMesh, Group, ShaderMaterial, BufferGeometry } from 'three';
import * as THREE from 'three';

interface CellRendererProps {
  position: [number, number, number];
}

const RIBOSOME_COUNT = 60;
const MRNA_COUNT = 20;
const FLAGELLA_SEGMENTS = 24;
const _dummy = new THREE.Object3D();

/* ── Membrane shader with vertex noise ── */
const membraneVert = /* glsl */ `
  uniform float uTime;
  uniform float uNoiseAmp;
  varying vec3 vNormal;
  varying vec3 vViewDir;
  varying float vNoise;

  // Simplex-ish hash
  vec3 hash3(vec3 p) {
    p = vec3(dot(p, vec3(127.1, 311.7, 74.7)),
             dot(p, vec3(269.5, 183.3, 246.1)),
             dot(p, vec3(113.5, 271.9, 124.6)));
    return -1.0 + 2.0 * fract(sin(p) * 43758.5453);
  }

  float noise3d(vec3 p) {
    vec3 i = floor(p);
    vec3 f = fract(p);
    vec3 u = f * f * (3.0 - 2.0 * f);
    return mix(
      mix(mix(dot(hash3(i), f),
              dot(hash3(i + vec3(1,0,0)), f - vec3(1,0,0)), u.x),
          mix(dot(hash3(i + vec3(0,1,0)), f - vec3(0,1,0)),
              dot(hash3(i + vec3(1,1,0)), f - vec3(1,1,0)), u.x), u.y),
      mix(mix(dot(hash3(i + vec3(0,0,1)), f - vec3(0,0,1)),
              dot(hash3(i + vec3(1,0,1)), f - vec3(1,0,1)), u.x),
          mix(dot(hash3(i + vec3(0,1,1)), f - vec3(0,1,1)),
              dot(hash3(i + vec3(1,1,1)), f - vec3(1,1,1)), u.x), u.y),
      u.z);
  }

  void main() {
    float n = noise3d(position * 3.0 + uTime * 0.3) * uNoiseAmp;
    vNoise = n;
    vec3 displaced = position + normal * n;
    vNormal = normalize(normalMatrix * normal);
    vec4 mv = modelViewMatrix * vec4(displaced, 1.0);
    vViewDir = normalize(-mv.xyz);
    gl_Position = projectionMatrix * mv;
  }
`;

const membraneFrag = /* glsl */ `
  uniform vec3 uColor;
  uniform vec3 uRimColor;
  uniform float uRimPower;
  varying vec3 vNormal;
  varying vec3 vViewDir;
  varying float vNoise;

  void main() {
    float f = 1.0 - abs(dot(vNormal, vViewDir));
    float rim = pow(f, uRimPower);
    // Mix rim color with slight noise variation
    vec3 col = mix(uColor * 0.2, uRimColor, rim);
    col += vNoise * 0.08;
    float alpha = rim * 0.7 + (1.0 - f) * 0.02;
    gl_FragColor = vec4(col, clamp(alpha, 0.0, 1.0));
  }
`;

export function CellRenderer({ position }: CellRendererProps) {
  const groupRef = useRef<Group>(null);
  const membraneRef = useRef<Mesh>(null);
  const ribosomeRef = useRef<InstancedMesh>(null);
  const mrnaRef = useRef<InstancedMesh>(null);
  const nucleoidRef = useRef<Mesh>(null);
  const glowRef = useRef<Mesh>(null);
  const flagellaRef = useRef<Mesh>(null);
  const state = useCellForgeStore((s) => s.state);

  const massRatio = state.cellMass / 1000;
  const scale = Math.pow(massRatio, 1 / 3);
  const elongation = 1 + state.replicationProgress * 0.4;
  const pinch = state.replicationProgress > 0.8
    ? 1 - (state.replicationProgress - 0.8) * 1.5
    : 1;

  const atp = state.metaboliteConcentrations.atp ?? 5;
  const growthNorm = Math.min(1, state.growthRate * 3600 * 5);
  const stressed = atp < 1;

  const membraneColor = useMemo(() => {
    if (stressed) return new THREE.Color(0.9, 0.25, 0.15);
    return new THREE.Color(0.15 + growthNorm * 0.15, 0.5 + growthNorm * 0.25, 0.55);
  }, [stressed, growthNorm]);

  const rimColor = useMemo(() => {
    if (stressed) return new THREE.Color(1.0, 0.4, 0.3);
    return new THREE.Color(0.15 + growthNorm * 0.1, 0.4 + growthNorm * 0.15, 0.55);
  }, [stressed, growthNorm]);

  const membraneUniforms = useMemo(() => ({
    uColor: { value: membraneColor },
    uRimColor: { value: rimColor },
    uRimPower: { value: 3.5 },
    uTime: { value: 0 },
    uNoiseAmp: { value: 0.04 },
  }), []);

  const ribosomePositions = useMemo(() => {
    const arr: [number, number, number][] = [];
    for (let i = 0; i < RIBOSOME_COUNT; i++) {
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      const r = 0.15 + Math.random() * 0.6;
      arr.push([
        r * Math.sin(phi) * Math.cos(theta),
        r * Math.sin(phi) * Math.sin(theta) * 0.75,
        r * Math.cos(phi),
      ]);
    }
    return arr;
  }, []);

  const mrnaData = useMemo(() => {
    const arr: { pos: [number, number, number]; dir: [number, number, number] }[] = [];
    for (let i = 0; i < MRNA_COUNT; i++) {
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      const r = 0.1 + Math.random() * 0.45;
      arr.push({
        pos: [
          r * Math.sin(phi) * Math.cos(theta),
          r * Math.sin(phi) * Math.sin(theta) * 0.7,
          r * Math.cos(phi),
        ],
        dir: [Math.cos(theta), 0, Math.sin(theta)],
      });
    }
    return arr;
  }, []);

  // Flagella geometry — a wavy tube behind the cell
  const flagellaGeom = useMemo(() => {
    const points: THREE.Vector3[] = [];
    for (let i = 0; i < FLAGELLA_SEGMENTS; i++) {
      const t = i / (FLAGELLA_SEGMENTS - 1);
      points.push(new THREE.Vector3(-1 - t * 2.5, 0, 0));
    }
    const curve = new THREE.CatmullRomCurve3(points);
    return new THREE.TubeGeometry(curve, FLAGELLA_SEGMENTS * 2, 0.012, 5, false);
  }, []);

  useFrame(() => {
    const t = performance.now() * 0.001;

    if (groupRef.current) {
      groupRef.current.rotation.y += 0.0008;
    }

    // Membrane
    if (membraneRef.current) {
      const mat = membraneRef.current.material as ShaderMaterial;
      mat.uniforms.uTime.value = t;
      mat.uniforms.uColor.value.copy(membraneColor);
      mat.uniforms.uRimColor.value.copy(rimColor);
      const breath = 1 + Math.sin(t * 1.2) * 0.008;
      membraneRef.current.scale.set(
        scale * elongation * breath,
        scale * 0.82 * pinch * breath,
        scale * breath,
      );
    }

    // Ribosomes
    if (ribosomeRef.current) {
      for (let i = 0; i < RIBOSOME_COUNT; i++) {
        const [bx, by, bz] = ribosomePositions[i];
        const j = 0.01 + growthNorm * 0.02;
        _dummy.position.set(
          bx + Math.sin(t * 2.2 + i * 1.1) * j,
          by + Math.cos(t * 2.8 + i * 0.7) * j,
          bz + Math.sin(t * 1.6 + i * 1.5) * j,
        );
        _dummy.scale.setScalar(0.035 + growthNorm * 0.015);
        _dummy.updateMatrix();
        ribosomeRef.current.setMatrixAt(i, _dummy.matrix);
      }
      ribosomeRef.current.instanceMatrix.needsUpdate = true;
    }

    // mRNA
    if (mrnaRef.current) {
      const totalMrna = Object.values(state.mrnaCounts).reduce((a, b) => a + b, 0);
      const activity = Math.min(1, totalMrna / 150);
      for (let i = 0; i < MRNA_COUNT; i++) {
        const m = mrnaData[i];
        const [bx, by, bz] = m.pos;
        const drift = Math.sin(t * 0.4 + i * 2.1) * 0.08 * activity;
        _dummy.position.set(
          bx + m.dir[0] * drift,
          by + Math.cos(t * 1.0 + i) * 0.025,
          bz + m.dir[2] * drift,
        );
        const len = 0.03 + activity * 0.07;
        _dummy.scale.set(0.012, len, 0.012);
        // Orient cylinder Y-axis along the radial direction
        const angle = Math.atan2(m.dir[2], m.dir[0]);
        _dummy.rotation.set(
          Math.sin(t * 0.7 + i) * 0.3,
          0,
          -Math.PI / 2 + angle + Math.cos(t * 0.5 + i) * 0.3,
        );
        _dummy.updateMatrix();
        mrnaRef.current.setMatrixAt(i, _dummy.matrix);
      }
      mrnaRef.current.instanceMatrix.needsUpdate = true;
    }

    // Nucleoid
    if (nucleoidRef.current) {
      const sz = 0.25 + state.replicationProgress * 0.08;
      nucleoidRef.current.scale.set(sz * 1.15, sz * 0.9, sz);
    }
    if (glowRef.current) {
      const sz = (0.25 + state.replicationProgress * 0.08) * 2.0;
      glowRef.current.scale.setScalar(sz);
    }

    // Animate flagella wave
    if (flagellaRef.current) {
      const geom = flagellaRef.current.geometry as BufferGeometry;
      const posArr = geom.attributes.position;
      if (posArr) {
        const orig = (geom as any)._origPositions;
        if (!orig) {
          (geom as any)._origPositions = Float32Array.from(posArr.array as Float32Array);
        } else {
          const arr = posArr.array as Float32Array;
          for (let i = 0; i < arr.length; i += 3) {
            const ox = orig[i];
            const progress = Math.abs(ox + 1) / 2.5; // 0 at cell, 1 at tip
            const wave = Math.sin(t * 6 - progress * 8) * 0.06 * progress;
            const wave2 = Math.cos(t * 4.5 - progress * 6) * 0.03 * progress;
            arr[i] = orig[i];
            arr[i + 1] = orig[i + 1] + wave;
            arr[i + 2] = orig[i + 2] + wave2;
          }
          posArr.needsUpdate = true;
          geom.computeBoundingSphere();
        }
      }
    }
  });

  return (
    <group ref={groupRef} position={position}>
      {/* Membrane */}
      <mesh ref={membraneRef} renderOrder={10}>
        <sphereGeometry args={[1, 64, 48]} />
        <shaderMaterial
          vertexShader={membraneVert}
          fragmentShader={membraneFrag}
          uniforms={membraneUniforms}
          transparent
          side={THREE.FrontSide}
          depthWrite={false}
        />
      </mesh>

      {/* Nucleoid */}
      <mesh ref={nucleoidRef} renderOrder={1}>
        <icosahedronGeometry args={[1, 2]} />
        <meshStandardMaterial
          color="#0a1540"
          emissive="#122266"
          emissiveIntensity={0.25 + state.replicationProgress * 0.3}
          roughness={0.95}
          metalness={0}
        />
      </mesh>

      {/* Nucleoid glow */}
      <mesh ref={glowRef} renderOrder={0}>
        <icosahedronGeometry args={[1, 1]} />
        <meshBasicMaterial
          color="#1a2266"
          transparent
          opacity={0.04}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
        />
      </mesh>

      {/* Replication fork */}
      {state.replicationProgress > 0.01 && (
        <mesh rotation={[Math.PI / 2, 0, 0]} scale={[0.32 * scale, 0.32 * scale, 0.015]} renderOrder={2}>
          <torusGeometry args={[1, 0.1, 6, 48, Math.PI * 2 * state.replicationProgress]} />
          <meshStandardMaterial
            color="#1a2244"
            emissive="#334488"
            emissiveIntensity={0.3}
          />
        </mesh>
      )}

      {/* Ribosomes */}
      <instancedMesh ref={ribosomeRef} args={[undefined, undefined, RIBOSOME_COUNT]} renderOrder={3}>
        <icosahedronGeometry args={[1, 0]} />
        <meshStandardMaterial
          color="#443010"
          emissive="#886620"
          emissiveIntensity={0.2 + growthNorm * 0.15}
          roughness={0.9}
        />
      </instancedMesh>

      {/* mRNA */}
      <instancedMesh ref={mrnaRef} args={[undefined, undefined, MRNA_COUNT]} renderOrder={4}>
        <cylinderGeometry args={[1, 0.4, 1, 3]} />
        <meshStandardMaterial
          color="#0a2a15"
          emissive="#186630"
          emissiveIntensity={0.2}
          roughness={0.9}
        />
      </instancedMesh>

      {/* Flagellum */}
      <mesh ref={flagellaRef} geometry={flagellaGeom} renderOrder={5}>
        <meshStandardMaterial
          color="#2a3844"
          emissive="#334455"
          emissiveIntensity={0.15}
          roughness={0.8}
        />
      </mesh>

    </group>
  );
}
