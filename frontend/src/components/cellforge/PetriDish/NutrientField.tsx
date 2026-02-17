import { useMemo } from 'react';
import { useCellForgeStore } from '@/stores/cellforgeStore';
import * as THREE from 'three';

export function NutrientField() {
  const glucose = useCellForgeStore((s) => s.state.metaboliteConcentrations.glucose ?? 0);
  const intensity = Math.min(1, glucose / 15);

  // Agar surface texture — subtle organic noise
  const agarTex = useMemo(() => {
    const size = 512;
    const canvas = document.createElement('canvas');
    canvas.width = size;
    canvas.height = size;
    const ctx = canvas.getContext('2d')!;

    // Base: very dark teal
    ctx.fillStyle = '#050a0e';
    ctx.fillRect(0, 0, size, size);

    // Add subtle noise spots
    for (let i = 0; i < 800; i++) {
      const x = Math.random() * size;
      const y = Math.random() * size;
      const r = 1 + Math.random() * 3;
      const alpha = 0.02 + Math.random() * 0.04;
      ctx.beginPath();
      ctx.arc(x, y, r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(40, 80, 60, ${alpha})`;
      ctx.fill();
    }

    // Radial nutrient gradient from center
    const g = ctx.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size * 0.45);
    g.addColorStop(0, 'rgba(20, 60, 50, 0.15)');
    g.addColorStop(0.5, 'rgba(10, 35, 30, 0.08)');
    g.addColorStop(1, 'rgba(0, 0, 0, 0)');
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, size, size);

    const tex = new THREE.CanvasTexture(canvas);
    tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
    return tex;
  }, []);

  // Dish rim ring
  const rimGeom = useMemo(() => {
    return new THREE.TorusGeometry(5, 0.08, 8, 64);
  }, []);

  return (
    <group>
      {/* Agar surface — circular dish */}
      <mesh position={[0, -0.35, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <circleGeometry args={[5, 64]} />
        <meshStandardMaterial
          map={agarTex}
          color={[0.03 + intensity * 0.02, 0.06 + intensity * 0.03, 0.05 + intensity * 0.01]}
          roughness={0.9}
          metalness={0}
        />
      </mesh>

      {/* Nutrient glow */}
      <mesh position={[0, -0.34, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <circleGeometry args={[3, 48]} />
        <meshBasicMaterial
          color={[0.05, 0.15 + intensity * 0.1, 0.1]}
          transparent
          opacity={0.06 + intensity * 0.08}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
        />
      </mesh>

      {/* Dish rim */}
      <mesh geometry={rimGeom} position={[0, -0.3, 0]} rotation={[Math.PI / 2, 0, 0]}>
        <meshStandardMaterial
          color="#556677"
          roughness={0.3}
          metalness={0.4}
        />
      </mesh>

      {/* Dish rim highlight (glass-like) */}
      <mesh geometry={rimGeom} position={[0, -0.25, 0]} rotation={[Math.PI / 2, 0, 0]} scale={[1.01, 1.01, 1.5]}>
        <meshStandardMaterial
          color="#aabbcc"
          transparent
          opacity={0.08}
          roughness={0.1}
          metalness={0.6}
        />
      </mesh>
    </group>
  );
}
