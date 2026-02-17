import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useParams } from "react-router-dom";
import { GenomeCircle } from "../components/GenomeCircle";
import { GeneDetail } from "../components/GeneDetail";
import { GenomeOverview } from "../components/GenomeOverview";
import { useGeneStore } from "../store";
import { useGenomeLoader } from "../hooks/useGenomes";
export function GenomeMapPage() {
    const { genomeId } = useParams();
    useGenomeLoader(genomeId);
    const { genome, selectedGene } = useGeneStore();
    if (!genome) {
        return _jsx("div", { className: "page-loading", children: "Loading genome map..." });
    }
    return (_jsxs("div", { className: "page genome-map-page", children: [_jsx(GenomeOverview, {}), _jsxs("div", { className: `genome-viz-grid ${selectedGene ? "gene-selected" : ""}`, children: [_jsxs("div", { className: "panel genome-circle-panel", children: [_jsx("h2", { className: "panel-title", children: "Genome Map" }), _jsx("p", { className: "panel-sub", children: "Click a gene to inspect it. Red = unknown function." }), _jsx(GenomeCircle, {})] }), selectedGene && (_jsx("div", { className: "right-stack", children: _jsx(GeneDetail, {}) }))] })] }));
}
