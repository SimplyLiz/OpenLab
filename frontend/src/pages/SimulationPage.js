import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useParams } from "react-router-dom";
import { SimulationDashboard } from "../components/SimulationDashboard";
import { CellSimulation } from "../components/CellSimulation";
import { useGeneStore } from "../store";
import { useGenomeLoader } from "../hooks/useGenomes";
export function SimulationPage() {
    const { genomeId } = useParams();
    useGenomeLoader(genomeId);
    const genome = useGeneStore((s) => s.genome);
    if (!genome) {
        return _jsx("div", { className: "page-loading", children: "Loading simulation..." });
    }
    return (_jsxs("div", { className: "page simulation-page", children: [_jsxs("div", { className: "panel cell-sim-panel", children: [_jsx("h2", { className: "panel-title", children: "Virtual Cell" }), _jsx("p", { className: "panel-sub", children: "Minimal synthetic cell \u2014 alive on screen" }), _jsx(CellSimulation, {})] }), _jsx(SimulationDashboard, {})] }));
}
