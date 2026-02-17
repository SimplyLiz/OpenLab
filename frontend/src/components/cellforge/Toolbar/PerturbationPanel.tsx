import { useState } from 'react';
import { useCellForgeStore } from '@/stores/cellforgeStore';

const GENES = [
  'dnaA', 'rpoB', 'rpsA', 'gyrA', 'ftsZ', 'pgi', 'pfkA', 'gapA',
  'eno', 'pykF', 'aceE', 'gltA', 'icd', 'sucA', 'sdhA', 'atpA',
];

export function PerturbationPanel() {
  const { knockedOut, knockout, restoreGene, setMediaGlucose, state } = useCellForgeStore();
  const [glucoseVal, setGlucoseVal] = useState(10);

  return (
    <div style={{ border: '1px solid #333', padding: 8, borderRadius: 4 }}>
      <h4 style={{ margin: '0 0 8px' }}>Perturbations</h4>

      {/* Gene knockout */}
      <div style={{ marginBottom: 8 }}>
        <div style={{ fontSize: 11, color: '#aaa', marginBottom: 4 }}>Gene Knockouts</div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
          {GENES.map((g) => {
            const isKO = knockedOut.has(g);
            return (
              <button
                key={g}
                onClick={() => isKO ? restoreGene(g) : knockout(g)}
                title={isKO ? `Restore ${g}` : `Knockout ${g}`}
                style={{
                  fontSize: 9,
                  padding: '2px 4px',
                  border: 'none',
                  borderRadius: 2,
                  background: isKO ? '#a33' : '#333',
                  color: isKO ? '#fcc' : '#999',
                  cursor: 'pointer',
                  textDecoration: isKO ? 'line-through' : 'none',
                }}
              >
                {g}
              </button>
            );
          })}
        </div>
        {knockedOut.size > 0 && (
          <div style={{ fontSize: 10, color: '#f88', marginTop: 4 }}>
            {knockedOut.size} gene(s) knocked out
          </div>
        )}
      </div>

      {/* Media shift */}
      <div>
        <div style={{ fontSize: 11, color: '#aaa', marginBottom: 4 }}>Media Glucose (mM)</div>
        <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
          <input
            type="range"
            min={0}
            max={50}
            step={0.5}
            value={glucoseVal}
            onChange={(e) => setGlucoseVal(parseFloat(e.target.value))}
            style={{ flex: 1 }}
          />
          <span style={{ fontSize: 11, color: '#fff', minWidth: 30 }}>{glucoseVal}</span>
          <button
            onClick={() => setMediaGlucose(glucoseVal)}
            style={{
              fontSize: 10, padding: '2px 6px', border: 'none',
              borderRadius: 2, background: '#448', color: '#fff', cursor: 'pointer',
            }}
          >
            Apply
          </button>
        </div>
        <div style={{ fontSize: 10, color: '#888', marginTop: 2 }}>
          Current: {(state.metaboliteConcentrations.glucose ?? 0).toFixed(1)} mM
        </div>
      </div>
    </div>
  );
}
