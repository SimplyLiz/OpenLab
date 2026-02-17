import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { useGeneStore } from "../store";
import { CellSimulation } from "./CellSimulation";
export function AppShell() {
    const petriPiP = useGeneStore((s) => s.petriPiP);
    const genome = useGeneStore((s) => s.genome);
    return (_jsxs("div", { className: "app-shell", children: [_jsx(Sidebar, {}), _jsx("main", { className: "app-main", children: _jsx(Outlet, {}) }), petriPiP && genome && (_jsx(PiPContainer, {}))] }));
}
function PiPContainer() {
    const setPetriPiP = useGeneStore((s) => s.setPetriPiP);
    const activeGenomeId = useGeneStore((s) => s.activeGenomeId);
    const handleClick = () => {
        setPetriPiP(false);
        if (activeGenomeId) {
            window.location.href = `/g/${activeGenomeId}/petri`;
        }
    };
    return (_jsx("div", { className: "pip-container", onClick: handleClick, title: "Click to return to Petri Dish", children: _jsx(CellSimulation, { compact: true }) }));
}
