import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useCellForgeStore } from '@/stores/cellforgeStore';
const W = 320;
const H = 140;
const PAD = { t: 20, r: 10, b: 24, l: 40 };
const COLORS = {
    glucose: '#4af', atp: '#f84', nadh: '#8f4', pyruvate: '#f4f', adp: '#fa4', nad: '#4ff',
};
const TRACKED = ['glucose', 'atp', 'nadh', 'pyruvate'];
export function MetaboliteChart() {
    const history = useCellForgeStore((s) => s.history);
    if (history.length < 2) {
        return (_jsxs("div", { style: { border: '1px solid #333', padding: 8, borderRadius: 4 }, children: [_jsx("h4", { style: { margin: '0 0 4px', fontSize: 12 }, children: "Metabolites" }), _jsx("div", { style: { color: '#666', fontSize: 11 }, children: "Press Play to see data" })] }));
    }
    const tMin = history[0].time;
    const tMax = history[history.length - 1].time;
    const tRange = tMax - tMin || 1;
    // Find y range across tracked metabolites
    let yMax = 1;
    for (const snap of history) {
        for (const m of TRACKED) {
            const v = snap.metaboliteConcentrations[m] ?? 0;
            if (v > yMax)
                yMax = v;
        }
    }
    yMax = Math.ceil(yMax * 1.1);
    const pw = W - PAD.l - PAD.r;
    const ph = H - PAD.t - PAD.b;
    const sx = (t) => PAD.l + ((t - tMin) / tRange) * pw;
    const sy = (v) => PAD.t + ph - (v / yMax) * ph;
    return (_jsxs("div", { style: { border: '1px solid #333', padding: 8, borderRadius: 4 }, children: [_jsx("h4", { style: { margin: '0 0 4px', fontSize: 12 }, children: "Metabolites (mM)" }), _jsxs("svg", { width: W, height: H, style: { display: 'block' }, children: [_jsx("line", { x1: PAD.l, y1: PAD.t, x2: PAD.l, y2: PAD.t + ph, stroke: "#444" }), _jsx("text", { x: PAD.l - 4, y: PAD.t + 4, textAnchor: "end", fill: "#888", fontSize: 9, children: yMax }), _jsx("text", { x: PAD.l - 4, y: PAD.t + ph, textAnchor: "end", fill: "#888", fontSize: 9, children: "0" }), _jsx("line", { x1: PAD.l, y1: PAD.t + ph, x2: PAD.l + pw, y2: PAD.t + ph, stroke: "#444" }), _jsxs("text", { x: PAD.l, y: H - 4, fill: "#888", fontSize: 9, children: [tMin.toFixed(0), "s"] }), _jsxs("text", { x: PAD.l + pw, y: H - 4, textAnchor: "end", fill: "#888", fontSize: 9, children: [tMax.toFixed(0), "s"] }), TRACKED.map((m) => {
                        const pts = history.map((snap) => `${sx(snap.time)},${sy(snap.metaboliteConcentrations[m] ?? 0)}`).join(' ');
                        return _jsx("polyline", { points: pts, fill: "none", stroke: COLORS[m] ?? '#888', strokeWidth: 1.5 }, m);
                    }), TRACKED.map((m, i) => (_jsxs("g", { transform: `translate(${PAD.l + i * 70}, ${PAD.t - 6})`, children: [_jsx("rect", { width: 8, height: 8, fill: COLORS[m] ?? '#888', rx: 1 }), _jsx("text", { x: 11, y: 7, fill: "#ccc", fontSize: 9, children: m })] }, m)))] })] }));
}
