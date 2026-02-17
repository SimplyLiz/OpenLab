import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState, useCallback } from "react";
import { useGeneStore } from "../../store";

export function PopulationControls() {
    const cellSpec = useGeneStore((s) => s.cellSpec);
    const isPopulationMode = useGeneStore((s) => s.isPopulationMode);
    const setPopulationMode = useGeneStore((s) => s.setPopulationMode);
    const populationSnapshots = useGeneStore((s) => s.populationSnapshots);

    const [gridSize, setGridSize] = useState(8);
    const [mutationRate, setMutationRate] = useState(-4); // log10 scale
    const [stochastic, setStochastic] = useState(true);
    const [seed, setSeed] = useState(42);
    const [isRunning, setIsRunning] = useState(false);

    const hasData = populationSnapshots.length > 0;
    const lastSnap = hasData ? populationSnapshots[populationSnapshots.length - 1] : null;

    const startColony = useCallback(async () => {
        if (!cellSpec) return;
        setIsRunning(true);
        setPopulationMode(true);

        try {
            const res = await fetch("/api/v1/simulation/population", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    cellspec: cellSpec,
                    grid_size: gridSize,
                    duration: 7200,
                    mutation_rate: Math.pow(10, mutationRate),
                    seed: seed,
                }),
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            useGeneStore.getState().setPopulationSnapshots(data.snapshots || []);
        } catch (err) {
            console.error("Population simulation failed:", err);
        } finally {
            setIsRunning(false);
        }
    }, [cellSpec, gridSize, mutationRate, seed, setPopulationMode]);

    const reset = useCallback(() => {
        setPopulationMode(false);
        useGeneStore.getState().setPopulationSnapshots([]);
    }, [setPopulationMode]);

    return (_jsxs("div", { className: "glass-panel population-controls", children: [
        _jsx("h3", { className: "glass-panel-title", children: "Colony Simulation" }),

        _jsxs("label", { className: "pop-control-row", children: [
            _jsx("span", { className: "pop-label", children: "Grid size" }),
            _jsx("input", {
                type: "range", min: 4, max: 16, value: gridSize,
                onChange: (e) => setGridSize(Number(e.target.value)),
                className: "pop-slider",
            }),
            _jsx("span", { className: "pop-value", children: `${gridSize}×${gridSize}` }),
        ] }),

        _jsxs("label", { className: "pop-control-row", children: [
            _jsx("span", { className: "pop-label", children: "Mutation rate" }),
            _jsx("input", {
                type: "range", min: -5, max: -2, step: 0.5, value: mutationRate,
                onChange: (e) => setMutationRate(Number(e.target.value)),
                className: "pop-slider",
            }),
            _jsx("span", { className: "pop-value", children: `1e${mutationRate}` }),
        ] }),

        _jsxs("label", { className: "pop-control-row", children: [
            _jsx("input", {
                type: "checkbox", checked: stochastic,
                onChange: (e) => setStochastic(e.target.checked),
            }),
            _jsx("span", { children: "Stochastic" }),
        ] }),

        _jsxs("div", { className: "pop-actions", children: [
            _jsx("button", {
                className: "knockout-btn knockout-run",
                onClick: startColony,
                disabled: !cellSpec || isRunning,
                children: isRunning ? "Simulating..." : "Start Colony",
            }),
            _jsx("button", {
                className: "knockout-btn knockout-reset",
                onClick: reset,
                disabled: !hasData && !isPopulationMode,
                children: "Reset",
            }),
        ] }),

        hasData && lastSnap && (_jsxs("div", { className: "colony-stats", children: [
            _jsxs("div", { className: "colony-stat-row", children: [
                _jsx("span", { className: "colony-stat-label", children: "Cells" }),
                _jsx("span", { className: "colony-stat-value", children: lastSnap.total_cells }),
            ] }),
            _jsxs("div", { className: "colony-stat-row", children: [
                _jsx("span", { className: "colony-stat-label", children: "Max gen" }),
                _jsx("span", { className: "colony-stat-value", children: lastSnap.generations_max }),
            ] }),
            _jsxs("div", { className: "colony-stat-row", children: [
                _jsx("span", { className: "colony-stat-label", children: "Mutations" }),
                _jsx("span", { className: "colony-stat-value", children: lastSnap.total_mutations }),
            ] }),
            _jsxs("div", { className: "colony-stat-row", children: [
                _jsx("span", { className: "colony-stat-label", children: "Mean fitness" }),
                _jsx("span", { className: "colony-stat-value", children: lastSnap.mean_fitness.toExponential(2) }),
            ] }),
        ] })),
    ] }));
}
