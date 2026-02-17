import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useCellForgeStore } from '@/stores/cellforgeStore';
const GENES = [
    'dnaA', 'rpoB', 'rpsA', 'gyrA', 'ftsZ', 'pgi', 'pfkA', 'gapA',
    'eno', 'pykF', 'aceE', 'gltA', 'icd', 'sucA', 'sdhA', 'atpA',
];
function valueToColor(value, max) {
    const t = Math.min(1, value / (max || 1));
    const r = Math.round(20 + t * 200);
    const g = Math.round(20 + (1 - Math.abs(t - 0.5) * 2) * 100);
    const b = Math.round(200 - t * 180);
    return `rgb(${r},${g},${b})`;
}
export function GeneExpressionHeatmap() {
    const state = useCellForgeStore((s) => s.state);
    const knockedOut = useCellForgeStore((s) => s.knockedOut);
    const maxMrna = Math.max(1, ...Object.values(state.mrnaCounts));
    const maxProtein = Math.max(1, ...Object.values(state.proteinCounts));
    return (_jsxs("div", { style: { border: '1px solid #333', padding: 8, borderRadius: 4 }, children: [_jsx("h4", { style: { margin: '0 0 4px', fontSize: 12 }, children: "Gene Expression" }), _jsxs("div", { style: { display: 'grid', gridTemplateColumns: '50px 40px 40px', gap: 1, fontSize: 9 }, children: [_jsx("div", { style: { color: '#888' }, children: "Gene" }), _jsx("div", { style: { color: '#888', textAlign: 'center' }, children: "mRNA" }), _jsx("div", { style: { color: '#888', textAlign: 'center' }, children: "Protein" }), GENES.map((g) => {
                        const mrna = state.mrnaCounts[g] ?? 0;
                        const prot = state.proteinCounts[g] ?? 0;
                        const isKO = knockedOut.has(g);
                        return [
                            _jsx("div", { style: { color: isKO ? '#f66' : '#ccc', textDecoration: isKO ? 'line-through' : 'none' }, children: g }, `${g}-name`),
                            _jsx("div", { style: {
                                    background: valueToColor(mrna, maxMrna),
                                    textAlign: 'center', color: '#fff', borderRadius: 1, padding: '1px 0',
                                }, children: mrna }, `${g}-mrna`),
                            _jsx("div", { style: {
                                    background: valueToColor(prot, maxProtein),
                                    textAlign: 'center', color: '#fff', borderRadius: 1, padding: '1px 0',
                                }, children: prot }, `${g}-prot`),
                        ];
                    })] })] }));
}
