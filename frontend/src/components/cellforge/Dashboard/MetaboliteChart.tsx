import { useCellForgeStore } from '@/stores/cellforgeStore';

const W = 320;
const H = 140;
const PAD = { t: 20, r: 10, b: 24, l: 40 };
const COLORS: Record<string, string> = {
  glucose: '#4af', atp: '#f84', nadh: '#8f4', pyruvate: '#f4f', adp: '#fa4', nad: '#4ff',
};
const TRACKED = ['glucose', 'atp', 'nadh', 'pyruvate'];

export function MetaboliteChart() {
  const history = useCellForgeStore((s) => s.history);

  if (history.length < 2) {
    return (
      <div style={{ border: '1px solid #333', padding: 8, borderRadius: 4 }}>
        <h4 style={{ margin: '0 0 4px', fontSize: 12 }}>Metabolites</h4>
        <div style={{ color: '#666', fontSize: 11 }}>Press Play to see data</div>
      </div>
    );
  }

  const tMin = history[0].time;
  const tMax = history[history.length - 1].time;
  const tRange = tMax - tMin || 1;

  // Find y range across tracked metabolites
  let yMax = 1;
  for (const snap of history) {
    for (const m of TRACKED) {
      const v = snap.metaboliteConcentrations[m] ?? 0;
      if (v > yMax) yMax = v;
    }
  }
  yMax = Math.ceil(yMax * 1.1);

  const pw = W - PAD.l - PAD.r;
  const ph = H - PAD.t - PAD.b;
  const sx = (t: number) => PAD.l + ((t - tMin) / tRange) * pw;
  const sy = (v: number) => PAD.t + ph - (v / yMax) * ph;

  return (
    <div style={{ border: '1px solid #333', padding: 8, borderRadius: 4 }}>
      <h4 style={{ margin: '0 0 4px', fontSize: 12 }}>Metabolites (mM)</h4>
      <svg width={W} height={H} style={{ display: 'block' }}>
        {/* Y axis */}
        <line x1={PAD.l} y1={PAD.t} x2={PAD.l} y2={PAD.t + ph} stroke="#444" />
        <text x={PAD.l - 4} y={PAD.t + 4} textAnchor="end" fill="#888" fontSize={9}>{yMax}</text>
        <text x={PAD.l - 4} y={PAD.t + ph} textAnchor="end" fill="#888" fontSize={9}>0</text>
        {/* X axis */}
        <line x1={PAD.l} y1={PAD.t + ph} x2={PAD.l + pw} y2={PAD.t + ph} stroke="#444" />
        <text x={PAD.l} y={H - 4} fill="#888" fontSize={9}>{tMin.toFixed(0)}s</text>
        <text x={PAD.l + pw} y={H - 4} textAnchor="end" fill="#888" fontSize={9}>{tMax.toFixed(0)}s</text>

        {/* Lines */}
        {TRACKED.map((m) => {
          const pts = history.map((snap) => `${sx(snap.time)},${sy(snap.metaboliteConcentrations[m] ?? 0)}`).join(' ');
          return <polyline key={m} points={pts} fill="none" stroke={COLORS[m] ?? '#888'} strokeWidth={1.5} />;
        })}

        {/* Legend */}
        {TRACKED.map((m, i) => (
          <g key={m} transform={`translate(${PAD.l + i * 70}, ${PAD.t - 6})`}>
            <rect width={8} height={8} fill={COLORS[m] ?? '#888'} rx={1} />
            <text x={11} y={7} fill="#ccc" fontSize={9}>{m}</text>
          </g>
        ))}
      </svg>
    </div>
  );
}
