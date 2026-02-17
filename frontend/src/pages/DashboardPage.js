import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useGeneStore } from "../store";
import { useGenomeLoader } from "../hooks/useGenomes";
import { CellSimulation } from "../components/CellSimulation";
const API = `${location.protocol}//${location.host}/api/v1`;
export function DashboardPage() {
    const { genomeId } = useParams();
    const navigate = useNavigate();
    useGenomeLoader(genomeId);
    const genome = useGeneStore((s) => s.genome);
    const simulationResult = useGeneStore((s) => s.simulationResult);
    const [summary, setSummary] = useState(null);
    useEffect(() => {
        fetch(`${API}/genes/research/summary`)
            .then((r) => (r.ok ? r.json() : null))
            .then((d) => { if (d)
            setSummary(d); })
            .catch(() => { });
    }, [genome]);
    if (!genome) {
        return _jsx("div", { className: "page-loading", children: "Loading dashboard..." });
    }
    const researchPct = summary
        ? Math.round(((summary.total_with_evidence) / Math.max(summary.total_stored, 1)) * 100)
        : 0;
    return (_jsxs("div", { className: "page dashboard-page", children: [_jsxs("div", { className: "dashboard-header", children: [_jsx("h1", { className: "dashboard-title", children: genome.organism }), _jsxs("p", { className: "dashboard-sub", children: [genome.accession, " \u2014 ", genome.description] })] }), _jsxs("div", { className: "stats-grid dashboard-kpi", children: [_jsxs("div", { className: "stat-card", children: [_jsx("div", { className: "stat-value", style: { color: "#22d3ee" }, children: genome.total_genes }), _jsx("div", { className: "stat-label", children: "Total Genes" })] }), _jsxs("div", { className: "stat-card", children: [_jsxs("div", { className: "stat-value", style: { color: "#34d399" }, children: [researchPct, "%"] }), _jsx("div", { className: "stat-label", children: "Researched" })] }), _jsxs("div", { className: "stat-card", children: [_jsx("div", { className: "stat-value", style: { color: "#a78bfa" }, children: simulationResult ? "Complete" : "Idle" }), _jsx("div", { className: "stat-label", children: "Simulation" })] }), _jsxs("div", { className: "stat-card", children: [_jsx("div", { className: "stat-value", style: { color: "#f87171" }, children: genome.genes_unknown }), _jsx("div", { className: "stat-label", children: "Unknown" })] })] }), _jsxs("div", { className: "dashboard-grid", children: [_jsxs("div", { className: "panel dashboard-categories", children: [_jsx("h2", { className: "panel-title", children: "Gene Categories" }), _jsx(CategoryBreakdown, { genome: genome })] }), _jsxs("div", { className: "panel dashboard-mini-petri", onClick: () => navigate(`/g/${genomeId}/petri`), style: { cursor: "pointer" }, children: [_jsx("h2", { className: "panel-title", children: "Virtual Cell" }), _jsx(CellSimulation, { compact: true })] })] }), summary && (_jsxs("div", { className: "panel dashboard-research", children: [_jsx("h2", { className: "panel-title", children: "Research Progress" }), _jsxs("div", { className: "dashboard-progress-grid", children: [_jsx(ProgressRing, { label: "Stored", value: summary.total_stored, total: genome.total_genes, color: "#94a3b8" }), _jsx(ProgressRing, { label: "Evidence", value: summary.total_with_evidence, total: genome.total_genes, color: "#22d3ee" }), _jsx(ProgressRing, { label: "Hypotheses", value: summary.total_with_hypothesis, total: genome.total_genes, color: "#fb923c" }), _jsx(ProgressRing, { label: "Graduated", value: summary.total_graduated, total: genome.total_genes, color: "#34d399" })] })] })), summary && summary.needs_review.length > 0 && (_jsxs("div", { className: "panel dashboard-activity", children: [_jsx("h2", { className: "panel-title", children: "Needs Review" }), _jsx("div", { className: "dashboard-feed", children: summary.needs_review.slice(0, 10).map((item) => (_jsxs("div", { className: "dashboard-feed-item", children: [_jsx("span", { className: "dashboard-feed-tag", children: item.locus_tag }), _jsx("span", { className: "dashboard-feed-title", children: item.hypothesis_title }), _jsx("span", { className: "dashboard-feed-conf", children: item.confidence != null ? `${(item.confidence * 100).toFixed(0)}%` : "—" })] }, item.locus_tag))) })] }))] }));
}
function CategoryBreakdown({ genome }) {
    const counts = {};
    for (const g of genome.genes) {
        counts[g.functional_category] = (counts[g.functional_category] || 0) + 1;
    }
    const COLORS = {
        gene_expression: "#22d3ee",
        cell_membrane: "#a78bfa",
        metabolism: "#34d399",
        genome_preservation: "#60a5fa",
        predicted: "#fb923c",
        unknown: "#f87171",
    };
    const LABELS = {
        gene_expression: "Gene Expression",
        cell_membrane: "Cell Membrane",
        metabolism: "Metabolism",
        genome_preservation: "Genome Preservation",
        predicted: "Predicted",
        unknown: "Unknown",
    };
    const total = genome.genes.length;
    return (_jsx("div", { className: "category-breakdown", children: Object.entries(counts)
            .sort((a, b) => b[1] - a[1])
            .map(([cat, count]) => (_jsxs("div", { className: "category-row", children: [_jsx("span", { className: "category-dot", style: { background: COLORS[cat] || "#888" } }), _jsx("span", { className: "category-label", children: LABELS[cat] || cat }), _jsx("span", { className: "category-bar-wrap", children: _jsx("span", { className: "category-bar", style: {
                            width: `${(count / total) * 100}%`,
                            background: COLORS[cat] || "#888",
                        } }) }), _jsx("span", { className: "category-count", children: count })] }, cat))) }));
}
function ProgressRing({ label, value, total, color, }) {
    const pct = total > 0 ? value / total : 0;
    const r = 36;
    const circ = 2 * Math.PI * r;
    const offset = circ * (1 - pct);
    return (_jsxs("div", { className: "progress-ring-item", children: [_jsxs("svg", { width: "88", height: "88", viewBox: "0 0 88 88", children: [_jsx("circle", { cx: "44", cy: "44", r: r, fill: "none", stroke: "rgba(255,255,255,0.06)", strokeWidth: "6" }), _jsx("circle", { cx: "44", cy: "44", r: r, fill: "none", stroke: color, strokeWidth: "6", strokeDasharray: circ, strokeDashoffset: offset, strokeLinecap: "round", transform: "rotate(-90 44 44)", style: { transition: "stroke-dashoffset 0.5s ease" } }), _jsx("text", { x: "44", y: "40", textAnchor: "middle", fill: "white", fontSize: "14", fontWeight: "600", children: value }), _jsxs("text", { x: "44", y: "54", textAnchor: "middle", fill: "#94a3b8", fontSize: "9", children: ["/ ", total] })] }), _jsx("div", { className: "progress-ring-label", children: label })] }));
}
