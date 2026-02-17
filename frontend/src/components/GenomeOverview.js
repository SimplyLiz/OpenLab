import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useGeneStore } from "../store";
const SOURCE_BADGE = {
    genbank: { label: "GenBank", color: "#34d399", bg: "rgba(52,211,153,0.12)" },
    dnasyn: { label: "DNASyn", color: "#fb923c", bg: "rgba(251,146,60,0.12)" },
    curated: { label: "Literature", color: "#2dd4bf", bg: "rgba(45,212,191,0.12)" },
    genelife: { label: "GeneLife", color: "#818cf8", bg: "rgba(129,140,248,0.12)" },
};
function SourceBadge({ source }) {
    const badge = SOURCE_BADGE[source];
    if (!badge)
        return null;
    return (_jsx("span", { className: "source-badge", style: { color: badge.color, backgroundColor: badge.bg }, children: badge.label }));
}
export function GenomeOverview() {
    const { genome, pipelinePhase, isAnalyzing, functionalAnalysis, predictions, selectGene, essentiality, cellSpec, validation } = useGeneStore();
    if (!genome)
        return null;
    // Count genes by category
    const categories = {};
    for (const gene of genome.genes) {
        const cat = gene.functional_category;
        if (!categories[cat]) {
            categories[cat] = { count: 0, color: gene.color };
        }
        categories[cat].count++;
    }
    const catLabels = {
        gene_expression: "Gene Expression",
        cell_membrane: "Cell Membrane",
        metabolism: "Metabolism",
        genome_preservation: "Genome Preservation",
        predicted: "Predicted",
        unknown: "Unknown",
    };
    const mysteryGenes = genome.genes.filter((g) => g.functional_category === "unknown");
    const predictedGenes = genome.genes.filter((g) => g.functional_category === "predicted");
    // Break predicted genes by source
    const curatedGenes = predictedGenes.filter((g) => g.prediction_source === "curated");
    const dnasynGenes = predictedGenes.filter((g) => g.prediction_source === "dnasyn");
    const genelifeGenes = predictedGenes.filter((g) => g.prediction_source === "genelife");
    return (_jsxs("div", { className: "panel genome-overview", children: [_jsx("h2", { className: "panel-title", children: genome.organism }), _jsx("p", { className: "summary", children: genome.description }), _jsxs("div", { className: "stats-grid", children: [_jsxs("div", { className: "stat-card", children: [_jsx("div", { className: "stat-value", children: genome.genome_length.toLocaleString() }), _jsx("div", { className: "stat-label", children: "base pairs" })] }), _jsxs("div", { className: "stat-card", children: [_jsx("div", { className: "stat-value", children: genome.total_genes }), _jsx("div", { className: "stat-label", children: "genes" })] }), _jsxs("div", { className: "stat-card", children: [_jsxs("div", { className: "stat-value", children: [genome.gc_content, "%"] }), _jsx("div", { className: "stat-label", children: "GC content" })] }), _jsxs("div", { className: "stat-card", children: [_jsx("div", { className: "stat-value", style: { color: "#34d399" }, children: genome.genes_known }), _jsx("div", { className: "stat-label", children: "original annotation" })] }), _jsxs("div", { className: "stat-card", children: [_jsx("div", { className: "stat-value", style: { color: "#f87171" }, children: mysteryGenes.length }), _jsx("div", { className: "stat-label", children: "still unknown" })] }), _jsxs("div", { className: "stat-card", children: [_jsx("div", { className: "stat-value", children: genome.is_circular ? "Circular" : "Linear" }), _jsx("div", { className: "stat-label", children: "topology" })] })] }), predictedGenes.length > 0 && (_jsxs("div", { className: "subsection findings-breakdown", children: [_jsx("h3", { children: "Our Findings" }), _jsxs("div", { className: "findings-row", children: [curatedGenes.length > 0 && (_jsxs("div", { className: "finding-stat", children: [_jsx("span", { className: "finding-count", style: { color: "#2dd4bf" }, children: curatedGenes.length }), _jsx(SourceBadge, { source: "curated" }), _jsx("span", { className: "finding-desc", children: "from published research" })] })), dnasynGenes.length > 0 && (_jsxs("div", { className: "finding-stat", children: [_jsx("span", { className: "finding-count", style: { color: "#fb923c" }, children: dnasynGenes.length }), _jsx(SourceBadge, { source: "dnasyn" }), _jsx("span", { className: "finding-desc", children: "evidence pipeline" })] })), genelifeGenes.length > 0 && (_jsxs("div", { className: "finding-stat", children: [_jsx("span", { className: "finding-count", style: { color: "#818cf8" }, children: genelifeGenes.length }), _jsx(SourceBadge, { source: "genelife" }), _jsx("span", { className: "finding-desc", children: "live analysis" })] }))] })] })), _jsxs("div", { className: "subsection", children: [_jsx("h3", { children: "Functional Categories" }), _jsx("div", { className: "category-bar", children: Object.entries(categories)
                            .sort((a, b) => b[1].count - a[1].count)
                            .map(([cat, { count, color }]) => (_jsx("div", { className: "cat-segment", style: { flex: count, backgroundColor: color }, title: `${catLabels[cat] ?? cat}: ${count} genes` }, cat))) }), _jsx("div", { className: "category-legend", children: Object.entries(categories)
                            .sort((a, b) => b[1].count - a[1].count)
                            .map(([cat, { count, color }]) => (_jsxs("span", { className: "cat-legend-item", children: [_jsx("span", { className: "cat-dot", style: { backgroundColor: color } }), catLabels[cat] ?? cat, ": ", count] }, cat))) })] }), isAnalyzing && pipelinePhase && (_jsxs("div", { className: "subsection pipeline-phase", children: [_jsx("h3", { children: "Evidence Pipeline" }), _jsx("div", { className: "phase-indicators", children: [1, 2, 3, 4, 5].map((p) => (_jsx("div", { className: `phase-dot ${p < pipelinePhase.phase ? "phase-done" : ""} ${p === pipelinePhase.phase ? "phase-active" : ""}`, children: p }, p))) }), _jsx("p", { className: "phase-message", children: pipelinePhase.message })] })), functionalAnalysis && functionalAnalysis.mean_convergence > 0 && (_jsxs("div", { className: "subsection convergence-summary", children: [_jsx("h3", { children: "Evidence Convergence" }), _jsxs("div", { className: "stats-grid", style: { gridTemplateColumns: "1fr 1fr 1fr" }, children: [_jsxs("div", { className: "stat-card", children: [_jsxs("div", { className: "stat-value", style: { color: "#22d3ee" }, children: [(functionalAnalysis.mean_convergence * 100).toFixed(1), "%"] }), _jsx("div", { className: "stat-label", children: "mean convergence" })] }), _jsxs("div", { className: "stat-card", children: [_jsx("div", { className: "stat-value", style: { color: "#a78bfa" }, children: functionalAnalysis.total_analyzed }), _jsx("div", { className: "stat-label", children: "genes analyzed" })] }), _jsxs("div", { className: "stat-card", children: [_jsx("div", { className: "stat-value", style: { color: "#34d399" }, children: functionalAnalysis.genes_with_hypothesis }), _jsx("div", { className: "stat-label", children: "AI hypotheses" })] })] })] })), _jsxs("div", { className: "subsection", children: [_jsxs("h3", { children: ["Still Unknown (", mysteryGenes.length, ")"] }), mysteryGenes.length === 0 ? (_jsx("p", { style: { color: "#34d399", fontStyle: "italic" }, children: "All mystery genes have been assigned predicted functions." })) : (_jsx("div", { className: "gene-table-scroll", children: _jsxs("table", { className: "data-table", children: [_jsx("thead", { children: _jsxs("tr", { children: [_jsx("th", { children: "Locus Tag" }), _jsx("th", { children: "Size" }), _jsx("th", { children: "Convergence" }), _jsx("th", { children: "Prediction" })] }) }), _jsx("tbody", { children: mysteryGenes
                                        .sort((a, b) => {
                                        const predA = predictions.get(a.locus_tag);
                                        const predB = predictions.get(b.locus_tag);
                                        return (predB?.convergence?.score ?? 0) - (predA?.convergence?.score ?? 0);
                                    })
                                        .slice(0, 50)
                                        .map((g) => {
                                        const pred = predictions.get(g.locus_tag);
                                        const conv = pred?.convergence?.score ?? 0;
                                        const hasHyp = !!pred?.hypothesis;
                                        return (_jsxs("tr", { className: "clickable-row", onClick: () => selectGene(g), children: [_jsx("td", { style: { color: "#f87171" }, children: g.locus_tag }), _jsxs("td", { children: [g.protein_length, "aa"] }), _jsx("td", { children: conv > 0 ? (_jsxs("span", { className: "conv-badge", style: {
                                                            color: conv >= 0.5 ? "#34d399" : conv >= 0.2 ? "#fbbf24" : "#fb923c",
                                                        }, children: [(conv * 100).toFixed(0), "%"] })) : (_jsx("span", { style: { color: "#475569" }, children: "\u2014" })) }), _jsx("td", { children: hasHyp ? (_jsx("span", { className: "hyp-badge", children: "AI" })) : pred?.predicted_function ? (_jsx("span", { className: "pred-text", children: pred.predicted_function.slice(0, 40) })) : (_jsx("span", { style: { color: "#475569" }, children: g.product || "unknown" })) })] }, g.locus_tag));
                                    }) })] }) }))] }), curatedGenes.length > 0 && (_jsx(PredictedTable, { title: "Literature-Curated", genes: curatedGenes, source: "curated", predictions: predictions, selectGene: selectGene })), dnasynGenes.length > 0 && (_jsx(PredictedTable, { title: "DNASyn Pipeline", genes: dnasynGenes, source: "dnasyn", predictions: predictions, selectGene: selectGene })), genelifeGenes.length > 0 && (_jsx(PredictedTable, { title: "GeneLife Analysis", genes: genelifeGenes, source: "genelife", predictions: predictions, selectGene: selectGene })), essentiality && (_jsxs("div", { className: "subsection", children: [_jsx("h3", { children: "Essentiality Prediction" }), _jsxs("div", { className: "stats-grid", style: { gridTemplateColumns: "1fr 1fr" }, children: [_jsxs("div", { className: "stat-card", children: [_jsx("div", { className: "stat-value", style: { color: "#f87171" }, children: essentiality.total_essential }), _jsx("div", { className: "stat-label", children: "essential genes" })] }), _jsxs("div", { className: "stat-card", children: [_jsx("div", { className: "stat-value", style: { color: "#34d399" }, children: essentiality.total_nonessential }), _jsx("div", { className: "stat-label", children: "non-essential genes" })] })] })] })), cellSpec && (_jsxs("div", { className: "subsection cellspec-summary", children: [_jsx("h3", { children: "CellSpec Assembly" }), _jsxs("div", { className: "stats-grid", children: [_jsxs("div", { className: "stat-card", children: [_jsx("div", { className: "stat-value", style: { color: "#22d3ee" }, children: cellSpec.genes?.length ?? 0 }), _jsx("div", { className: "stat-label", children: "genes" })] }), _jsxs("div", { className: "stat-card", children: [_jsx("div", { className: "stat-value", style: { color: "#a78bfa" }, children: cellSpec.reactions?.length ?? 0 }), _jsx("div", { className: "stat-label", children: "reactions" })] }), _jsxs("div", { className: "stat-card", children: [_jsx("div", { className: "stat-value", style: { color: "#34d399" }, children: cellSpec.metabolites?.length ?? 0 }), _jsx("div", { className: "stat-label", children: "metabolites" })] })] }), cellSpec.provenance_summary && (_jsx("p", { className: "cellspec-provenance", children: Object.entries(cellSpec.provenance_summary)
                            .map(([k, v]) => `${k}: ${v}`)
                            .join(" · ") }))] })), validation && (_jsxs("div", { className: "subsection validation-results", children: [_jsxs("h3", { children: ["Validation", _jsxs("span", { className: "validation-score", style: {
                                    color: validation.overall_score >= 0.7 ? "#34d399"
                                        : validation.overall_score >= 0.4 ? "#fbbf24"
                                            : "#f87171",
                                }, children: [(validation.overall_score * 100).toFixed(0), "% pass rate"] })] }), validation.doubling_time_hours != null && (_jsxs("p", { className: "validation-doubling", children: ["Doubling time: ", _jsxs("strong", { children: [validation.doubling_time_hours.toFixed(1), "h"] }), " ", "(expected ~2h)"] })), _jsx("div", { className: "validation-checks", children: validation.checks.map((check, i) => (_jsxs("div", { className: `validation-check ${check.passed ? "check-pass" : "check-fail"}`, children: [_jsx("span", { className: "check-icon", children: check.passed ? "\u2713" : "\u2717" }), _jsx("span", { className: "check-name", children: check.name }), check.actual && _jsx("span", { className: "check-details", children: check.actual })] }, i))) })] }))] }));
}
function PredictedTable({ title, genes, source, predictions, selectGene, }) {
    const badge = SOURCE_BADGE[source];
    return (_jsxs("div", { className: "subsection", children: [_jsxs("h3", { children: [_jsx(SourceBadge, { source: source }), " ", title, " (", genes.length, ")"] }), _jsx("div", { className: "gene-table-scroll", children: _jsxs("table", { className: "data-table", children: [_jsx("thead", { children: _jsxs("tr", { children: [_jsx("th", { children: "Locus Tag" }), _jsx("th", { children: "Predicted Function" }), _jsx("th", { children: "Confidence" }), _jsx("th", { children: "Tier" })] }) }), _jsx("tbody", { children: genes
                                .sort((a, b) => {
                                const predA = predictions.get(a.locus_tag);
                                const predB = predictions.get(b.locus_tag);
                                return (predB?.convergence?.confidence_tier ?? 4) - (predA?.convergence?.confidence_tier ?? 4) || 0;
                            })
                                .slice(0, 50)
                                .map((g) => {
                                const pred = predictions.get(g.locus_tag);
                                return (_jsxs("tr", { className: "clickable-row", onClick: () => selectGene(g), children: [_jsx("td", { style: { color: badge?.color ?? "#94a3b8" }, children: g.locus_tag }), _jsx("td", { className: "pred-cell", children: pred?.predicted_function || g.product }), _jsx("td", { children: _jsx("span", { style: {
                                                    color: pred?.confidence === "high" ? "#34d399"
                                                        : pred?.confidence === "medium" ? "#fbbf24"
                                                            : "#fb923c",
                                                }, children: pred?.confidence || "—" }) }), _jsx("td", { children: pred?.convergence?.confidence_tier ? (_jsxs("span", { className: `tier-badge tier-${pred.convergence.confidence_tier}`, children: ["T", pred.convergence.confidence_tier] })) : "—" })] }, g.locus_tag));
                            }) })] }) })] }));
}
