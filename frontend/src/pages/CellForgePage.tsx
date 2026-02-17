import { PetriDish } from '@/components/cellforge/PetriDish/PetriDish';
import { Dashboard } from '@/components/cellforge/Dashboard/Dashboard';
import { Toolbar } from '@/components/cellforge/Toolbar/Toolbar';
import { GenomeBrowser } from '@/components/cellforge/GenomeBrowser/GenomeBrowser';

export function CellForgePage() {
  return (
    <div style={{ display: 'flex', height: 'calc(100vh - 3rem)', background: '#111', color: '#eee' }}>
      {/* Left panel: controls */}
      <div style={{ width: 280, borderRight: '1px solid #333', overflow: 'auto' }}>
        <Toolbar />
      </div>

      {/* Center: 3D viewport */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        <div style={{ flex: 1 }}>
          <PetriDish />
        </div>
        {/* Footer: genome browser */}
        <div style={{ height: 180, borderTop: '1px solid #333', overflow: 'auto' }}>
          <GenomeBrowser />
        </div>
      </div>

      {/* Right panel: dashboard */}
      <div style={{ width: 360, borderLeft: '1px solid #333', overflow: 'auto' }}>
        <Dashboard />
      </div>
    </div>
  );
}
