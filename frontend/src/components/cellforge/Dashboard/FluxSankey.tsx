import { useCellForgeStore } from '@/stores/cellforgeStore';

const W = 320;
const H = 100;

export function FluxSankey() {
  const state = useCellForgeStore((s) => s.state);
  const history = useCellForgeStore((s) => s.history);

  const growthRate = state.growthRate;
  const flux = state.fluxDistribution;
  const glcFlux = flux.glucose_uptake ?? 0;
  const atpFlux = flux.atp_synthase ?? 0;

  if (history.length < 2) {
    return (
      <div style={{ border: '1px solid #333', padding: 8, borderRadius: 4 }}>
        <h4 style={{ margin: '0 0 4px', fontSize: 12 }}>Metabolic Flux</h4>
        <div style={{ color: '#666', fontSize: 11 }}>Press Play to see data</div>
      </div>
    );
  }

  // Simple growth curve from history
  const tMin = history[0].time;
  const tMax = history[history.length - 1].time;
  const tRange = tMax - tMin || 1;
  let mMax = 1;
  for (const s of history) { if (s.cellMass > mMax) mMax = s.cellMass; }
  mMax *= 1.1;

  const pw = W - 50;
  const ph = H - 30;
  const pts = history.map((s) => {
    const x = 40 + ((s.time - tMin) / tRange) * pw;
    const y = 10 + ph - (s.cellMass / mMax) * ph;
    return `${x},${y}`;
  }).join(' ');

  return (
    <div style={{ border: '1px solid #333', padding: 8, borderRadius: 4 }}>
      <h4 style={{ margin: '0 0 4px', fontSize: 12 }}>Growth & Flux</h4>
      <div style={{ display: 'flex', gap: 12, fontSize: 10, color: '#aaa', marginBottom: 4 }}>
        <span>Glc uptake: <b style={{ color: '#4af' }}>{glcFlux.toFixed(2)}</b> mmol/gDW/h</span>
        <span>ATP synth: <b style={{ color: '#f84' }}>{atpFlux.toFixed(1)}</b></span>
        <span>Growth: <b style={{ color: '#6f6' }}>{(growthRate * 3600).toFixed(4)}</b>/h</span>
      </div>
      <svg width={W} height={H} style={{ display: 'block' }}>
        <line x1={40} y1={10} x2={40} y2={10 + ph} stroke="#444" />
        <line x1={40} y1={10 + ph} x2={40 + pw} y2={10 + ph} stroke="#444" />
        <text x={36} y={14} textAnchor="end" fill="#888" fontSize={8}>{mMax.toFixed(0)}</text>
        <text x={36} y={10 + ph} textAnchor="end" fill="#888" fontSize={8}>0</text>
        <polyline points={pts} fill="none" stroke="#6f6" strokeWidth={1.5} />
        <text x={40 + pw / 2} y={H - 2} textAnchor="middle" fill="#888" fontSize={8}>Cell Mass (fg)</text>
      </svg>
    </div>
  );
}
