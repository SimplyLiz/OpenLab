import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from "react";
import { useGeneStore } from "../../store";
export function MetricsOverlay() {
    const [tab, setTab] = useState("growth");
    const simulationSnapshots = useGeneStore((s) => s.simulationSnapshots);
    const knockoutSimResult = useGeneStore((s) => s.knockoutSimResult);
    const hasData = simulationSnapshots.length > 1;
    const koSeries = knockoutSimResult?.time_series ?? [];
    if (!hasData && koSeries.length === 0) {
        return (_jsxs("div", { className: "glass-panel metrics-overlay", children: [_jsx("h3", { className: "glass-panel-title", children: "Metrics" }), _jsx("p", { className: "metrics-empty", children: "Run a simulation to see metrics" })] }));
    }
    const tabs = [
        { key: "growth", label: "Growth" },
        { key: "metabolites", label: "Meta" },
        { key: "expression", label: "Expr" },
        { key: "rate", label: "Rate" },
    ];
    return (_jsxs("div", { className: "glass-panel metrics-overlay", children: [_jsx("h3", { className: "glass-panel-title", children: "Metrics" }), _jsx("div", { className: "metrics-tabs", children: tabs.map((t) => (_jsx("button", { className: `metrics-tab ${tab === t.key ? "metrics-tab-active" : ""}`, onClick: () => setTab(t.key), children: t.label }, t.key))) }), _jsx("div", { className: "metrics-chart-area", children: _jsx(MiniChart, { tab: tab, snapshots: simulationSnapshots, koSnapshots: koSeries }) })] }));
}
function MiniChart({ tab, snapshots, koSnapshots, }) {
    // Select data field based on tab
    const fieldMap = {
        growth: { field: "volume", label: "Volume (fL)", color: "#22d3ee" },
        metabolites: { field: "atp", label: "ATP (mM)", color: "#fdd835" },
        expression: { field: "total_protein", label: "Total Protein", color: "#4fc3f7" },
        rate: { field: "growth_rate", label: "Growth Rate", color: "#34d399" },
    };
    const { field, label, color } = fieldMap[tab];
    // Extract values
    const values = snapshots.map((s) => s[field]);
    if (values.length < 2)
        return null;
    const minV = Math.min(...values);
    const maxV = Math.max(...values);
    const range = maxV - minV || 1;
    const w = 260;
    const h = 120;
    // Build SVG path
    const points = values.map((v, i) => {
        const x = (i / (values.length - 1)) * w;
        const y = h - ((v - minV) / range) * (h - 10) - 5;
        return `${x},${y}`;
    });
    const path = `M${points.join(" L")}`;
    // KO overlay if available
    let koPath = "";
    if (koSnapshots.length > 1) {
        const koValues = koSnapshots.map((s) => s[field]);
        if (koValues.length > 1 && koValues[0] != null) {
            const koPoints = koValues.map((v, i) => {
                const x = (i / (koValues.length - 1)) * w;
                const y = h - ((v - minV) / range) * (h - 10) - 5;
                return `${x},${y}`;
            });
            koPath = `M${koPoints.join(" L")}`;
        }
    }
    return (_jsxs("div", { className: "mini-chart", children: [_jsx("div", { className: "mini-chart-label", children: label }), _jsxs("svg", { width: w, height: h, viewBox: `0 0 ${w} ${h}`, children: [_jsx("path", { d: path, fill: "none", stroke: color, strokeWidth: "1.5", opacity: "0.9" }), koPath && (_jsx("path", { d: koPath, fill: "none", stroke: "#f87171", strokeWidth: "1.5", opacity: "0.7", strokeDasharray: "4 2" }))] }), koPath && (_jsxs("div", { className: "mini-chart-legend", children: [_jsx("span", { style: { color }, children: "WT" }), _jsx("span", { style: { color: "#f87171" }, children: "KO" })] }))] }));
}
