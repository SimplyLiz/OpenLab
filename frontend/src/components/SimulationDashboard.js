import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useGeneStore } from "../store";
import { GrowthChart } from "./charts/GrowthChart";
import { MetaboliteChart } from "./charts/MetaboliteChart";
import { ExpressionChart } from "./charts/ExpressionChart";
import { GrowthRateChart } from "./charts/GrowthRateChart";
export function SimulationDashboard() {
    const { simulationSnapshots, simulationResult, simulationProgress, simulationWallTime } = useGeneStore();
    // Don't render until we have simulation data
    if (simulationSnapshots.length < 2 && simulationProgress === 0)
        return null;
    const summary = simulationResult?.summary;
    const doublingTime = summary?.doubling_time_hours;
    const totalDivisions = simulationResult?.total_divisions ?? 0;
    return (_jsxs("div", { className: "panel sim-dashboard", children: [_jsx("h2", { className: "panel-title", children: "Whole-Cell Simulation" }), _jsxs("p", { className: "panel-sub", children: [simulationProgress < 1
                        ? `Simulating... ${(simulationProgress * 100).toFixed(0)}% (${simulationWallTime.toFixed(1)}s)`
                        : `Complete — ${totalDivisions} divisions`, doublingTime != null && ` — doubling time: ${doublingTime.toFixed(1)}h`] }), summary && (_jsxs("div", { className: "stats-grid sim-stats", children: [_jsxs("div", { className: "stat-card", children: [_jsx("div", { className: "stat-value", style: { color: "#22d3ee" }, children: totalDivisions }), _jsx("div", { className: "stat-label", children: "divisions" })] }), doublingTime != null && (_jsxs("div", { className: "stat-card", children: [_jsxs("div", { className: "stat-value", style: { color: "#34d399" }, children: [doublingTime.toFixed(1), "h"] }), _jsx("div", { className: "stat-label", children: "doubling time" })] })), _jsxs("div", { className: "stat-card", children: [_jsxs("div", { className: "stat-value", style: { color: "#fb923c" }, children: [(summary.wall_time_seconds ?? simulationWallTime).toFixed(1), "s"] }), _jsx("div", { className: "stat-label", children: "wall time" })] }), _jsxs("div", { className: "stat-card", children: [_jsx("div", { className: "stat-value", style: { color: "#a78bfa" }, children: simulationSnapshots.length }), _jsx("div", { className: "stat-label", children: "snapshots" })] })] })), _jsxs("div", { className: "sim-charts-grid", children: [_jsx("div", { className: "sim-chart-panel", children: _jsx(GrowthChart, { snapshots: simulationSnapshots }) }), _jsx("div", { className: "sim-chart-panel", children: _jsx(MetaboliteChart, { snapshots: simulationSnapshots }) }), _jsx("div", { className: "sim-chart-panel", children: _jsx(ExpressionChart, { snapshots: simulationSnapshots }) }), _jsx("div", { className: "sim-chart-panel", children: _jsx(GrowthRateChart, { snapshots: simulationSnapshots }) })] })] }));
}
