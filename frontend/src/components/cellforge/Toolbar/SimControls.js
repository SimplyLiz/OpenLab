import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useCellForgeStore } from '@/stores/cellforgeStore';
export function SimControls() {
    const { state, isRunning, speed, play, pause, stepOnce, reset, setSpeed } = useCellForgeStore();
    return (_jsxs("div", { style: { border: '1px solid #333', padding: 8, borderRadius: 4 }, children: [_jsx("h4", { style: { margin: '0 0 8px' }, children: "Simulation" }), _jsxs("div", { style: { display: 'flex', gap: 4, marginBottom: 8 }, children: [isRunning ? (_jsx("button", { onClick: pause, style: btnStyle('#c44'), children: "Pause" })) : (_jsx("button", { onClick: play, style: btnStyle('#4a4'), children: "Play" })), _jsx("button", { onClick: stepOnce, disabled: isRunning, style: btnStyle('#668'), children: "Step" }), _jsx("button", { onClick: reset, style: btnStyle('#666'), children: "Reset" })] }), _jsx("div", { style: { marginBottom: 8 }, children: _jsxs("label", { style: { fontSize: 11, color: '#aaa' }, children: ["Speed: ", speed, "x", _jsx("input", { type: "range", min: 0.1, max: 10, step: 0.1, value: speed, onChange: (e) => setSpeed(parseFloat(e.target.value)), style: { width: '100%', marginTop: 2 } })] }) }), _jsxs("div", { style: { fontSize: 11, color: '#aaa', lineHeight: 1.6 }, children: [_jsxs("div", { children: ["Time: ", _jsxs("span", { style: { color: '#fff' }, children: [state.time.toFixed(1), "s"] })] }), _jsxs("div", { children: ["Growth: ", _jsxs("span", { style: { color: '#6f6' }, children: [(state.growthRate * 3600).toFixed(4), "/h"] })] }), _jsxs("div", { children: ["Mass: ", _jsxs("span", { style: { color: '#fff' }, children: [state.cellMass.toFixed(0), " fg"] })] }), _jsxs("div", { children: ["Replication: ", _jsxs("span", { style: { color: '#88f' }, children: [(state.replicationProgress * 100).toFixed(1), "%"] })] })] })] }));
}
function btnStyle(bg) {
    return {
        padding: '4px 10px',
        border: 'none',
        borderRadius: 3,
        background: bg,
        color: '#fff',
        cursor: 'pointer',
        fontSize: 12,
        fontWeight: 600,
    };
}
