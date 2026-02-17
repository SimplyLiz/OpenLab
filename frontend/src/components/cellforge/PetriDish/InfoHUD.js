import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useCellForgeStore } from '@/stores/cellforgeStore';
export function InfoHUD() {
    const state = useCellForgeStore((s) => s.state);
    const isRunning = useCellForgeStore((s) => s.isRunning);
    const knockedOut = useCellForgeStore((s) => s.knockedOut);
    const totalMrna = Object.values(state.mrnaCounts).reduce((a, b) => a + b, 0);
    const totalProtein = Object.values(state.proteinCounts).reduce((a, b) => a + b, 0);
    const atp = state.metaboliteConcentrations.atp ?? 0;
    const glucose = state.metaboliteConcentrations.glucose ?? 0;
    return (_jsxs("div", { style: {
            position: 'absolute',
            top: 8,
            left: 8,
            right: 8,
            display: 'flex',
            justifyContent: 'space-between',
            pointerEvents: 'none',
            fontSize: 10,
        }, children: [_jsxs("div", { style: {
                    background: 'rgba(0,0,0,0.6)',
                    padding: '6px 10px',
                    borderRadius: 4,
                    display: 'flex',
                    gap: 16,
                    color: '#ccc',
                }, children: [_jsxs("div", { children: [_jsx("span", { style: { color: '#888' }, children: "Status " }), _jsx("span", { style: { color: isRunning ? '#6f6' : '#888' }, children: isRunning ? 'RUNNING' : 'PAUSED' })] }), _jsxs("div", { children: [_jsx("span", { style: { color: '#888' }, children: "ATP " }), _jsxs("span", { style: { color: atp > 3 ? '#f84' : atp > 1 ? '#fa4' : '#f44' }, children: [atp.toFixed(1), " mM"] })] }), _jsxs("div", { children: [_jsx("span", { style: { color: '#888' }, children: "Glucose " }), _jsxs("span", { style: { color: '#4af' }, children: [glucose.toFixed(1), " mM"] })] }), _jsxs("div", { children: [_jsx("span", { style: { color: '#888' }, children: "mRNA " }), _jsx("span", { style: { color: '#4c8' }, children: totalMrna })] }), _jsxs("div", { children: [_jsx("span", { style: { color: '#888' }, children: "Proteins " }), _jsx("span", { style: { color: '#c84' }, children: totalProtein })] }), knockedOut.size > 0 && (_jsx("div", { children: _jsxs("span", { style: { color: '#f66' }, children: [knockedOut.size, " KO"] }) }))] }), _jsxs("div", { style: {
                    background: 'rgba(0,0,0,0.6)',
                    padding: '6px 10px',
                    borderRadius: 4,
                    color: '#888',
                    lineHeight: 1.6,
                }, children: [_jsxs("div", { children: [_jsx("span", { style: { color: '#c94', fontSize: 8 }, children: "\u25CF" }), " Ribosomes"] }), _jsxs("div", { children: [_jsx("span", { style: { color: '#4c8', fontSize: 8 }, children: "\u25CF" }), " mRNA"] }), _jsxs("div", { children: [_jsx("span", { style: { color: '#56a', fontSize: 8 }, children: "\u25CF" }), " Nucleoid"] })] })] }));
}
