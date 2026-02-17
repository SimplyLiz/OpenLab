import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useParams } from "react-router-dom";
import { ResearchSidebar } from "../components/ResearchSidebar";
import { GeneDetail } from "../components/GeneDetail";
import { useGeneStore } from "../store";
import { useGenomeLoader } from "../hooks/useGenomes";
export function ResearchPage() {
    const { genomeId } = useParams();
    useGenomeLoader(genomeId);
    const genome = useGeneStore((s) => s.genome);
    const selectedGene = useGeneStore((s) => s.selectedGene);
    if (!genome) {
        return _jsx("div", { className: "page-loading", children: "Loading research..." });
    }
    return (_jsxs("div", { className: "page research-page", children: [_jsx(ResearchSidebar, {}), _jsx("div", { className: "research-detail", children: selectedGene ? (_jsx(GeneDetail, {})) : (_jsxs("div", { className: "research-empty-state", children: [_jsx("div", { className: "research-empty-icon", children: "\uD83D\uDD2C" }), _jsx("p", { children: "Select a gene from the queue to view research details" })] })) })] }));
}
