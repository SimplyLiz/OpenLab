import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useGeneStore } from "../store";
export function AnnotationPanel() {
    const { annotation } = useGeneStore();
    if (!annotation)
        return null;
    const { function_summary, go_terms, diseases, pathways, drugs, pubmed_count } = annotation;
    // Group GO terms by category
    const goByCategory = go_terms.reduce((acc, term) => {
        const cat = term.category || "unknown";
        (acc[cat] ??= []).push(term);
        return acc;
    }, {});
    const categoryLabels = {
        molecular_function: "Molecular Function",
        biological_process: "Biological Process",
        cellular_component: "Cellular Component",
        unknown: "Other",
    };
    return (_jsxs("div", { className: "panel annotation-panel", children: [_jsx("h2", { className: "panel-title", children: "Annotation & Function" }), function_summary && (_jsxs("div", { className: "subsection", children: [_jsx("h3", { children: "Function" }), _jsx("p", { children: function_summary })] })), _jsxs("div", { className: "stats-grid", children: [_jsxs("div", { className: "stat-card", children: [_jsx("div", { className: "stat-value", children: pubmed_count.toLocaleString() }), _jsx("div", { className: "stat-label", children: "PubMed articles" })] }), _jsxs("div", { className: "stat-card", children: [_jsx("div", { className: "stat-value", children: go_terms.length }), _jsx("div", { className: "stat-label", children: "GO terms" })] }), _jsxs("div", { className: "stat-card", children: [_jsx("div", { className: "stat-value", children: diseases.length }), _jsx("div", { className: "stat-label", children: "Disease links" })] }), _jsxs("div", { className: "stat-card", children: [_jsx("div", { className: "stat-value", children: pathways.length }), _jsx("div", { className: "stat-label", children: "Pathways" })] })] }), Object.entries(goByCategory).map(([cat, terms]) => (_jsxs("div", { className: "subsection", children: [_jsx("h3", { children: categoryLabels[cat] ?? cat }), _jsxs("div", { className: "tag-list", children: [terms.slice(0, 15).map((t) => (_jsx("span", { className: "go-tag", title: `${t.go_id} [${t.evidence}]`, children: t.name }, t.go_id))), terms.length > 15 && (_jsxs("span", { className: "more-tag", children: ["+", terms.length - 15, " more"] }))] })] }, cat))), diseases.length > 0 && (_jsxs("div", { className: "subsection", children: [_jsx("h3", { children: "Disease Associations" }), _jsx("ul", { className: "disease-list", children: diseases.map((d, i) => (_jsxs("li", { children: [_jsx("strong", { children: d.disease }), _jsx("span", { className: "source-badge", children: d.source }), d.mim_id && _jsxs("span", { className: "mim-id", children: ["MIM:", d.mim_id] })] }, i))) })] })), pathways.length > 0 && (_jsxs("div", { className: "subsection", children: [_jsx("h3", { children: "Pathways" }), _jsx("div", { className: "tag-list", children: pathways.map((p) => (_jsxs("span", { className: "pathway-tag", title: p.pathway_id, children: [p.name, _jsx("span", { className: "source-badge small", children: p.source })] }, p.pathway_id))) })] })), drugs.length > 0 && (_jsxs("div", { className: "subsection", children: [_jsx("h3", { children: "Drug Targets" }), _jsx("ul", { className: "drug-list", children: drugs.map((d, i) => (_jsxs("li", { children: [_jsx("strong", { children: d.drug_name }), d.action && _jsx("span", { className: "drug-action", children: d.action }), d.status && _jsx("span", { className: "source-badge", children: d.status })] }, i))) })] }))] }));
}
