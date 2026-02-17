import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect } from "react";
import { useParams } from "react-router-dom";
import { useGeneStore } from "../store";
import { useGenomeLoader } from "../hooks/useGenomes";
import { CellSimulation } from "../components/CellSimulation";
import { KnockoutLab } from "../components/petri/KnockoutLab";
import { MetricsOverlay } from "../components/petri/MetricsOverlay";
import { PlaybackBar } from "../components/petri/PlaybackBar";
export function PetriDishPage() {
    const { genomeId } = useParams();
    useGenomeLoader(genomeId);
    const genome = useGeneStore((s) => s.genome);
    const setPetriPiP = useGeneStore((s) => s.setPetriPiP);
    // When entering Petri Dish, disable PiP
    useEffect(() => {
        setPetriPiP(false);
        return () => {
            // When leaving, enable PiP
            setPetriPiP(true);
        };
    }, [setPetriPiP]);
    if (!genome) {
        return _jsx("div", { className: "page-loading", children: "Loading Petri Dish..." });
    }
    return (_jsxs("div", { className: "petri-dish-page", children: [_jsx("div", { className: "petri-canvas-container", children: _jsx(CellSimulation, {}) }), _jsxs("div", { className: "petri-overlay", children: [_jsx("div", { className: "petri-top-bar", children: _jsxs("div", { className: "petri-genome-badge", children: [_jsx("span", { className: "petri-badge-accession", children: genome.accession }), _jsx("span", { className: "petri-badge-organism", children: genome.organism })] }) }), _jsxs("div", { className: "petri-bottom-panels", children: [_jsx(KnockoutLab, {}), _jsx("div", { className: "petri-spacer" }), _jsx(MetricsOverlay, {})] }), _jsx(PlaybackBar, {})] })] }));
}
