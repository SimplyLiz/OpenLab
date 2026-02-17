import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from 'react';
import { useCellForgeStore } from '@/stores/cellforgeStore';
const GENES = [
    'dnaA', 'rpoB', 'rpsA', 'gyrA', 'ftsZ', 'pgi', 'pfkA', 'gapA',
    'eno', 'pykF', 'aceE', 'gltA', 'icd', 'sucA', 'sdhA', 'atpA',
];
export function PerturbationPanel() {
    const { knockedOut, knockout, restoreGene, setMediaGlucose, state } = useCellForgeStore();
    const [glucoseVal, setGlucoseVal] = useState(10);
    return (_jsxs("div", { style: { border: '1px solid #333', padding: 8, borderRadius: 4 }, children: [_jsx("h4", { style: { margin: '0 0 8px' }, children: "Perturbations" }), _jsxs("div", { style: { marginBottom: 8 }, children: [_jsx("div", { style: { fontSize: 11, color: '#aaa', marginBottom: 4 }, children: "Gene Knockouts" }), _jsx("div", { style: { display: 'flex', flexWrap: 'wrap', gap: 2 }, children: GENES.map((g) => {
                            const isKO = knockedOut.has(g);
                            return (_jsx("button", { onClick: () => isKO ? restoreGene(g) : knockout(g), title: isKO ? `Restore ${g}` : `Knockout ${g}`, style: {
                                    fontSize: 9,
                                    padding: '2px 4px',
                                    border: 'none',
                                    borderRadius: 2,
                                    background: isKO ? '#a33' : '#333',
                                    color: isKO ? '#fcc' : '#999',
                                    cursor: 'pointer',
                                    textDecoration: isKO ? 'line-through' : 'none',
                                }, children: g }, g));
                        }) }), knockedOut.size > 0 && (_jsxs("div", { style: { fontSize: 10, color: '#f88', marginTop: 4 }, children: [knockedOut.size, " gene(s) knocked out"] }))] }), _jsxs("div", { children: [_jsx("div", { style: { fontSize: 11, color: '#aaa', marginBottom: 4 }, children: "Media Glucose (mM)" }), _jsxs("div", { style: { display: 'flex', gap: 4, alignItems: 'center' }, children: [_jsx("input", { type: "range", min: 0, max: 50, step: 0.5, value: glucoseVal, onChange: (e) => setGlucoseVal(parseFloat(e.target.value)), style: { flex: 1 } }), _jsx("span", { style: { fontSize: 11, color: '#fff', minWidth: 30 }, children: glucoseVal }), _jsx("button", { onClick: () => setMediaGlucose(glucoseVal), style: {
                                    fontSize: 10, padding: '2px 6px', border: 'none',
                                    borderRadius: 2, background: '#448', color: '#fff', cursor: 'pointer',
                                }, children: "Apply" })] }), _jsxs("div", { style: { fontSize: 10, color: '#888', marginTop: 2 }, children: ["Current: ", (state.metaboliteConcentrations.glucose ?? 0).toFixed(1), " mM"] })] })] }));
}
