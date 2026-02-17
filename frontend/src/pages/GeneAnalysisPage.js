import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { GeneOverview } from "../components/GeneOverview";
import { SequencePanel } from "../components/SequencePanel";
import { AnnotationPanel } from "../components/AnnotationPanel";
import { useGeneStore } from "../store";
export function GeneAnalysisPage() {
    const { geneRecord } = useGeneStore();
    if (!geneRecord) {
        return _jsx("div", { className: "page-loading", children: "No gene loaded. Use the search to analyze a gene." });
    }
    return (_jsxs("div", { className: "page gene-analysis-page", children: [_jsx(GeneOverview, {}), _jsxs("div", { className: "analysis-grid", children: [_jsx(SequencePanel, {}), _jsx(AnnotationPanel, {})] })] }));
}
