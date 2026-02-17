import { useState } from 'react';
import { useCellForgeStore } from '@/stores/cellforgeStore';
import { GeneDetail } from './GeneDetail';

const GENES = [
  { id: 'dnaA', start: 0, end: 900, product: 'Replication initiator' },
  { id: 'rpoB', start: 1000, end: 1900, product: 'RNA polymerase beta' },
  { id: 'rpsA', start: 2000, end: 2900, product: 'Ribosomal protein S1' },
  { id: 'gyrA', start: 3000, end: 3900, product: 'DNA gyrase' },
  { id: 'ftsZ', start: 4000, end: 4900, product: 'Cell division protein' },
  { id: 'pgi', start: 5000, end: 5900, product: 'Glucose-6-P isomerase' },
  { id: 'pfkA', start: 6000, end: 6900, product: 'Phosphofructokinase' },
  { id: 'gapA', start: 7000, end: 7900, product: 'GAPDH' },
  { id: 'eno', start: 8000, end: 8900, product: 'Enolase' },
  { id: 'pykF', start: 9000, end: 9900, product: 'Pyruvate kinase' },
  { id: 'aceE', start: 10000, end: 10900, product: 'Pyruvate dehydrogenase' },
  { id: 'gltA', start: 11000, end: 11900, product: 'Citrate synthase' },
  { id: 'icd', start: 12000, end: 12900, product: 'Isocitrate dehydrogenase' },
  { id: 'sucA', start: 13000, end: 13900, product: '2-oxoglutarate DH' },
  { id: 'sdhA', start: 14000, end: 14900, product: 'Succinate DH' },
  { id: 'atpA', start: 15000, end: 15900, product: 'ATP synthase alpha' },
];

const TOTAL_LEN = 16000;
const W = 800;
const TRACK_H = 24;

export function GenomeBrowser() {
  const [selected, setSelected] = useState<string | null>(null);
  const state = useCellForgeStore((s) => s.state);
  const knockedOut = useCellForgeStore((s) => s.knockedOut);

  const maxMrna = Math.max(1, ...Object.values(state.mrnaCounts));

  return (
    <div style={{ padding: 8, height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
        <h4 style={{ margin: 0, fontSize: 12 }}>Genome Browser</h4>
        <span style={{ fontSize: 10, color: '#888' }}>{TOTAL_LEN.toLocaleString()} bp</span>
      </div>

      {/* Gene track */}
      <svg width="100%" height={TRACK_H + 20} viewBox={`0 0 ${W} ${TRACK_H + 20}`} style={{ minWidth: 400 }}>
        {/* Backbone */}
        <line x1={0} y1={TRACK_H / 2} x2={W} y2={TRACK_H / 2} stroke="#444" strokeWidth={2} />

        {/* Genes */}
        {GENES.map((gene) => {
          const x = (gene.start / TOTAL_LEN) * W;
          const w = ((gene.end - gene.start) / TOTAL_LEN) * W;
          const mrna = state.mrnaCounts[gene.id] ?? 0;
          const exprLevel = mrna / maxMrna;
          const isKO = knockedOut.has(gene.id);
          const isSel = selected === gene.id;

          const color = isKO ? '#a33' : `hsl(${120 + exprLevel * 120}, 70%, ${30 + exprLevel * 30}%)`;

          return (
            <g key={gene.id} onClick={() => setSelected(isSel ? null : gene.id)} style={{ cursor: 'pointer' }}>
              <rect
                x={x} y={2} width={w} height={TRACK_H - 4}
                rx={3} fill={color}
                stroke={isSel ? '#fff' : 'none'} strokeWidth={isSel ? 1.5 : 0}
              />
              <text
                x={x + w / 2} y={TRACK_H + 14}
                textAnchor="middle" fill="#aaa" fontSize={8}
              >
                {gene.id}
              </text>
            </g>
          );
        })}
      </svg>

      {/* Gene detail */}
      {selected && (
        <GeneDetail
          geneId={selected}
          product={GENES.find((g) => g.id === selected)?.product ?? ''}
          mrna={state.mrnaCounts[selected] ?? 0}
          protein={state.proteinCounts[selected] ?? 0}
          isKO={knockedOut.has(selected)}
        />
      )}
    </div>
  );
}
