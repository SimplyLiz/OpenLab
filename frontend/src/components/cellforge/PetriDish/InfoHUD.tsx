import { useCellForgeStore } from '@/stores/cellforgeStore';

export function InfoHUD() {
  const state = useCellForgeStore((s) => s.state);
  const isRunning = useCellForgeStore((s) => s.isRunning);
  const knockedOut = useCellForgeStore((s) => s.knockedOut);

  const totalMrna = Object.values(state.mrnaCounts).reduce((a, b) => a + b, 0);
  const totalProtein = Object.values(state.proteinCounts).reduce((a, b) => a + b, 0);
  const atp = state.metaboliteConcentrations.atp ?? 0;
  const glucose = state.metaboliteConcentrations.glucose ?? 0;

  return (
    <div style={{
      position: 'absolute',
      top: 8,
      left: 8,
      right: 8,
      display: 'flex',
      justifyContent: 'space-between',
      pointerEvents: 'none',
      fontSize: 10,
    }}>
      {/* Top-left: cell status */}
      <div style={{
        background: 'rgba(0,0,0,0.6)',
        padding: '6px 10px',
        borderRadius: 4,
        display: 'flex',
        gap: 16,
        color: '#ccc',
      }}>
        <div>
          <span style={{ color: '#888' }}>Status </span>
          <span style={{ color: isRunning ? '#6f6' : '#888' }}>{isRunning ? 'RUNNING' : 'PAUSED'}</span>
        </div>
        <div>
          <span style={{ color: '#888' }}>ATP </span>
          <span style={{ color: atp > 3 ? '#f84' : atp > 1 ? '#fa4' : '#f44' }}>{atp.toFixed(1)} mM</span>
        </div>
        <div>
          <span style={{ color: '#888' }}>Glucose </span>
          <span style={{ color: '#4af' }}>{glucose.toFixed(1)} mM</span>
        </div>
        <div>
          <span style={{ color: '#888' }}>mRNA </span>
          <span style={{ color: '#4c8' }}>{totalMrna}</span>
        </div>
        <div>
          <span style={{ color: '#888' }}>Proteins </span>
          <span style={{ color: '#c84' }}>{totalProtein}</span>
        </div>
        {knockedOut.size > 0 && (
          <div>
            <span style={{ color: '#f66' }}>{knockedOut.size} KO</span>
          </div>
        )}
      </div>

      {/* Top-right: legend */}
      <div style={{
        background: 'rgba(0,0,0,0.6)',
        padding: '6px 10px',
        borderRadius: 4,
        color: '#888',
        lineHeight: 1.6,
      }}>
        <div><span style={{ color: '#c94', fontSize: 8 }}>&#9679;</span> Ribosomes</div>
        <div><span style={{ color: '#4c8', fontSize: 8 }}>&#9679;</span> mRNA</div>
        <div><span style={{ color: '#56a', fontSize: 8 }}>&#9679;</span> Nucleoid</div>
      </div>
    </div>
  );
}
