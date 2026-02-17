import { Canvas } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import { CellRenderer } from './CellRenderer';
import { NutrientField } from './NutrientField';
import { MetaboliteParticles } from './MetaboliteParticles';
import { InfoHUD } from './InfoHUD';

export function PetriDish() {
  return (
    <div style={{ width: '100%', height: '100%', position: 'relative', background: '#020206' }}>
      <Canvas
        camera={{ position: [0, 2, 3.8], fov: 50 }}
        gl={{ antialias: true, alpha: false }}
        style={{ background: '#020206' }}
      >
        {/* Dim microscope-style lighting — organelles rely on emissive, not reflected light */}
        <ambientLight intensity={0.03} color="#334455" />
        <directionalLight position={[1, 8, 2]} intensity={0.15} color="#8899aa" />
        <directionalLight position={[-2, 3, -3]} intensity={0.06} color="#334466" />

        <CellRenderer position={[0, 0.15, 0]} />
        <MetaboliteParticles />
        <NutrientField />

        <OrbitControls
          minDistance={1.8}
          maxDistance={10}
          enablePan={false}
          autoRotate
          autoRotateSpeed={0.3}
          maxPolarAngle={Math.PI * 0.45}
          minPolarAngle={Math.PI * 0.15}
        />
      </Canvas>

      <InfoHUD />
    </div>
  );
}
