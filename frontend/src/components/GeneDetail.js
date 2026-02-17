import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
import { useState, useEffect } from "react";
import { useGeneStore } from "../store";
import { useGeneAnalysis } from "../hooks/useGeneAnalysis";
import { useResearch } from "../hooks/useResearch";
const SOURCE_INFO = {
    genbank: { label: "GenBank", color: "#34d399", bg: "rgba(52,211,153,0.12)", desc: "Original NCBI annotation" },
    dnasyn: { label: "DNASyn", color: "#fb923c", bg: "rgba(251,146,60,0.12)", desc: "DNASyn evidence pipeline" },
    curated: { label: "Literature", color: "#2dd4bf", bg: "rgba(45,212,191,0.12)", desc: "Expert-curated from published research" },
    genelife: { label: "GeneLife", color: "#818cf8", bg: "rgba(129,140,248,0.12)", desc: "GeneLife live analysis" },
};
const CATEGORY_LABELS = {
    gene_expression: "Gene Expression",
    cell_membrane: "Cell Membrane",
    metabolism: "Metabolism",
    genome_preservation: "Genome Preservation",
    predicted: "Predicted Function",
    unknown: "Unknown Function",
};
const SOURCE_LABELS = {
    protein_features: "Protein Properties",
    cdd: "CDD Domains",
    ncbi_blast: "BLAST Homology",
    interpro: "InterPro",
    string: "STRING Network",
    uniprot: "UniProt",
    literature: "Literature",
};
const TIER_LABELS = {
    1: { label: "HIGH", color: "#34d399" },
    2: { label: "MODERATE", color: "#fbbf24" },
    3: { label: "LOW", color: "#fb923c" },
    4: { label: "FLAGGED", color: "#f87171" },
};
export function GeneDetail() {
    const { selectedGene, selectGene, predictions, essentiality, kinetics, cellSpec, geneAnalysisStatus, geneAnalysisProgress, geneAnalysisMessage, geneAnalysisTarget, researchStatus, } = useGeneStore();
    const { analyzeGene } = useGeneAnalysis();
    const { fetchResearch, approveGene, rejectGene, correctGene } = useResearch();
    const [correctInput, setCorrectInput] = useState("");
    const [showCorrectForm, setShowCorrectForm] = useState(false);
    const [actionPending, setActionPending] = useState(false);
    const [showStoredEvidence, setShowStoredEvidence] = useState(false);
    const g = selectedGene;
    // Fetch research status when gene changes
    useEffect(() => {
        if (g) {
            fetchResearch(g.locus_tag);
        }
    }, [g?.locus_tag, fetchResearch]);
    if (!g)
        return null;
    const research = researchStatus.get(g.locus_tag);
    const prediction = predictions.get(g.locus_tag);
    const isBeingAnalyzed = geneAnalysisTarget === g.locus_tag && geneAnalysisStatus === "running";
    const canReanalyze = g.functional_category === "unknown" || g.is_hypothetical;
    const isEssential = essentiality?.predictions[g.locus_tag];
    const geneKinetics = kinetics?.kinetics?.find((k) => k.reaction_id === `rxn_${g.locus_tag}`);
    const csGene = cellSpec?.genes?.find((cg) => cg.locus_tag === g.locus_tag);
    return (_jsxs("div", { className: "panel gene-detail", children: [_jsxs("div", { className: "gene-detail-header", children: [_jsxs("h2", { className: "panel-title", children: [_jsx("span", { style: { color: g.color }, children: g.locus_tag }), g.gene_name && _jsx("span", { className: "gene-name", children: g.gene_name })] }), _jsx("button", { className: "close-btn", onClick: () => selectGene(null), children: "X" })] }), g.prediction_source && SOURCE_INFO[g.prediction_source] && (_jsxs("div", { className: "source-indicator", style: {
                    borderLeftColor: SOURCE_INFO[g.prediction_source].color,
                    backgroundColor: SOURCE_INFO[g.prediction_source].bg,
                }, children: [_jsx("span", { className: "source-badge", style: {
                            color: SOURCE_INFO[g.prediction_source].color,
                            backgroundColor: "transparent",
                            fontWeight: 600,
                        }, children: SOURCE_INFO[g.prediction_source].label }), _jsx("span", { className: "source-desc", children: SOURCE_INFO[g.prediction_source].desc })] })), _jsxs("div", { className: "id-grid", children: [_jsxs("div", { className: "id-tag", children: [_jsx("span", { className: "id-label", children: "Category" }), _jsx("span", { className: "id-value", style: { color: g.color }, children: CATEGORY_LABELS[g.functional_category] ?? g.functional_category })] }), _jsxs("div", { className: "id-tag", children: [_jsx("span", { className: "id-label", children: "Position" }), _jsxs("span", { className: "id-value", children: [g.start.toLocaleString(), "\u2013", g.end.toLocaleString(), " (", g.strand === 1 ? "+" : "-", ")"] })] }), _jsxs("div", { className: "id-tag", children: [_jsx("span", { className: "id-label", children: "Length" }), _jsxs("span", { className: "id-value", children: [g.protein_length, " aa"] })] })] }), _jsxs("div", { className: "subsection", children: [_jsx("h3", { children: "Product" }), _jsxs("p", { style: { color: g.is_hypothetical ? "#f87171" : "#e2e8f0" }, children: [g.product || "No annotation", g.is_hypothetical && _jsx("span", { className: "mystery-badge", children: "MYSTERY" })] })] }), isBeingAnalyzed && (_jsxs("div", { className: "gene-analysis-progress", children: [_jsx("h3", { children: "Analyzing..." }), _jsx("div", { className: "gene-analysis-bar", children: _jsx("div", { className: "gene-analysis-fill", style: { width: `${Math.max(geneAnalysisProgress * 100, 2)}%` } }) }), _jsx("p", { className: "gene-analysis-msg", children: geneAnalysisMessage })] })), canReanalyze && !isBeingAnalyzed && prediction && prediction.evidence.length > 1 && (_jsx("div", { className: "subsection", children: _jsx("button", { className: "reanalyze-btn", onClick: () => analyzeGene(g), children: "Re-analyze" }) })), isEssential !== undefined && (_jsx("div", { className: "subsection", children: _jsx("span", { className: "essentiality-badge", style: {
                        color: isEssential ? "#f87171" : "#34d399",
                        backgroundColor: isEssential ? "rgba(248,113,113,0.12)" : "rgba(52,211,153,0.12)",
                    }, children: isEssential ? "ESSENTIAL" : "Non-essential" }) })), geneKinetics && (_jsxs("div", { className: "subsection kinetics-detail", children: [_jsx("h3", { children: "Enzyme Kinetics" }), _jsxs("div", { className: "kinetics-grid", children: [_jsxs("div", { className: "kinetics-item", children: [_jsx("span", { className: "kinetics-label", children: "EC" }), _jsx("span", { className: "kinetics-value", children: geneKinetics.ec_number })] }), _jsxs("div", { className: "kinetics-item", children: [_jsxs("span", { className: "kinetics-label", children: ["k", _jsx("sub", { children: "cat" })] }), _jsxs("span", { className: "kinetics-value", children: [geneKinetics.kcat.value.toFixed(2), " s", _jsx("sup", { children: "-1" })] })] }), Object.entries(geneKinetics.km ?? {}).slice(0, 3).map(([met, val]) => (_jsxs("div", { className: "kinetics-item", children: [_jsxs("span", { className: "kinetics-label", children: ["K", _jsx("sub", { children: "m" }), " ", met] }), _jsxs("span", { className: "kinetics-value", children: [val.value.toFixed(3), " mM"] })] }, met))), _jsxs("div", { className: "kinetics-item", children: [_jsx("span", { className: "kinetics-label", children: "Source" }), _jsx("span", { className: "kinetics-value kinetics-source", children: geneKinetics.source })] }), _jsxs("div", { className: "kinetics-item", children: [_jsx("span", { className: "kinetics-label", children: "Trust" }), _jsx("span", { className: "kinetics-value", style: {
                                            color: geneKinetics.trust_level === "measured" ? "#34d399"
                                                : geneKinetics.trust_level === "computed" ? "#fbbf24"
                                                    : "#fb923c",
                                        }, children: geneKinetics.trust_level })] })] })] })), csGene && csGene.expression_rate != null && (_jsxs("div", { className: "subsection", children: [_jsx("h3", { children: "CellSpec" }), _jsx("div", { className: "kinetics-grid", children: _jsxs("div", { className: "kinetics-item", children: [_jsx("span", { className: "kinetics-label", children: "Expression rate" }), _jsx("span", { className: "kinetics-value", children: csGene.expression_rate.toFixed(4) })] }) })] })), prediction && _jsx(PredictionPanel, { prediction: prediction }), _jsx(ResearchActionsPanel, { research: research, prediction: prediction, actionPending: actionPending, showCorrectForm: showCorrectForm, correctInput: correctInput, showStoredEvidence: showStoredEvidence, onApprove: async () => {
                    setActionPending(true);
                    await approveGene(g.locus_tag);
                    setActionPending(false);
                }, onReject: async () => {
                    setActionPending(true);
                    await rejectGene(g.locus_tag);
                    setActionPending(false);
                }, onCorrectToggle: () => setShowCorrectForm(!showCorrectForm), onCorrectInput: setCorrectInput, onCorrectSubmit: async () => {
                    if (!correctInput.trim())
                        return;
                    setActionPending(true);
                    await correctGene(g.locus_tag, correctInput.trim());
                    setActionPending(false);
                    setShowCorrectForm(false);
                    setCorrectInput("");
                }, onToggleEvidence: () => setShowStoredEvidence(!showStoredEvidence) }), g.protein_sequence && (_jsxs("div", { className: "subsection", children: [_jsx("h3", { children: "Protein Sequence" }), _jsx("div", { className: "sequence-block", children: g.protein_sequence.match(/.{1,60}/g)?.map((line, i) => (_jsxs("div", { className: "seq-line", children: [_jsx("span", { className: "seq-pos", children: (i * 60 + 1).toString().padStart(4) }), line.split("").map((aa, j) => (_jsx("span", { className: `aa aa-${getAAClass(aa)}`, children: aa }, j)))] }, i))) })] }))] }));
}
function PredictionPanel({ prediction }) {
    const conv = prediction.convergence;
    const tier = TIER_LABELS[conv.confidence_tier] || TIER_LABELS[3];
    return (_jsxs(_Fragment, { children: [_jsxs("div", { className: "subsection convergence-section", children: [_jsx("h3", { children: "Convergence Analysis" }), _jsxs("div", { className: "convergence-bar-container", children: [_jsx("div", { className: "convergence-meter", children: _jsx("div", { className: "convergence-fill", style: {
                                        width: `${Math.min(conv.score * 100, 100)}%`,
                                        backgroundColor: tier.color,
                                    } }) }), _jsxs("div", { className: "convergence-stats", children: [_jsxs("span", { className: "conv-score", children: [(conv.score * 100).toFixed(1), "%"] }), _jsxs("span", { className: "conv-tier", style: { color: tier.color }, children: ["Tier ", conv.confidence_tier, ": ", tier.label] }), _jsxs("span", { className: "conv-sources", children: [conv.n_evidence_sources, " sources"] })] })] })] }), prediction.hypothesis && (_jsx(HypothesisPanel, { hypothesis: prediction.hypothesis })), prediction.evidence_summary.length > 0 && (_jsxs("div", { className: "subsection", children: [_jsx("h3", { children: "Evidence Summary" }), _jsx("ul", { className: "evidence-summary-list", children: prediction.evidence_summary.map((line, i) => (_jsx("li", { children: line }, i))) })] })), prediction.evidence.length > 0 && (_jsxs("div", { className: "subsection", children: [_jsxs("h3", { children: ["Evidence Sources (", prediction.evidence.length, ")"] }), _jsx("div", { className: "evidence-sources", children: prediction.evidence.map((ev, i) => (_jsx(EvidenceCard, { evidence: ev }, i))) })] }))] }));
}
function HypothesisPanel({ hypothesis }) {
    return (_jsxs("div", { className: "subsection hypothesis-section", children: [_jsxs("h3", { children: ["AI Hypothesis", _jsxs("span", { className: "hypothesis-confidence", children: ["confidence: ", (hypothesis.confidence_score * 100).toFixed(0), "%"] })] }), _jsx("div", { className: "hypothesis-function", children: hypothesis.predicted_function || "No prediction generated" }), hypothesis.suggested_category && (_jsxs("div", { className: "hypothesis-category", children: ["Suggested: ", CATEGORY_LABELS[hypothesis.suggested_category] || hypothesis.suggested_category] }))] }));
}
function EvidenceCard({ evidence }) {
    const sourceLabel = SOURCE_LABELS[evidence.source] || evidence.source;
    const hasGO = evidence.go_terms.length > 0;
    const hasEC = evidence.ec_numbers.length > 0;
    const hasCats = evidence.categories.length > 0;
    return (_jsxs("div", { className: "evidence-card", children: [_jsx("div", { className: "evidence-source", children: sourceLabel }), hasGO && (_jsxs("div", { className: "evidence-terms", children: [_jsx("span", { className: "term-label", children: "GO:" }), evidence.go_terms.slice(0, 5).map((t) => (_jsx("span", { className: "term-chip go-chip", children: t }, t))), evidence.go_terms.length > 5 && (_jsxs("span", { className: "term-more", children: ["+", evidence.go_terms.length - 5] }))] })), hasEC && (_jsxs("div", { className: "evidence-terms", children: [_jsx("span", { className: "term-label", children: "EC:" }), evidence.ec_numbers.map((ec) => (_jsx("span", { className: "term-chip ec-chip", children: ec }, ec)))] })), hasCats && (_jsxs("div", { className: "evidence-terms", children: [_jsx("span", { className: "term-label", children: "Categories:" }), evidence.categories.slice(0, 3).map((c) => (_jsx("span", { className: "term-chip cat-chip", children: c }, c)))] })), !hasGO && !hasEC && !hasCats && evidence.keywords.length > 0 && (_jsxs("div", { className: "evidence-terms", children: [_jsx("span", { className: "term-label", children: "Keywords:" }), evidence.keywords.slice(0, 5).map((k) => (_jsx("span", { className: "term-chip kw-chip", children: k }, k)))] }))] }));
}
const RESEARCH_BADGE = {
    not_stored: { label: "Not Stored", color: "#64748b" },
    stored: { label: "Stored", color: "#60a5fa" },
    review: { label: "Under Review", color: "#fbbf24" },
    graduated: { label: "Graduated", color: "#34d399" },
    rejected: { label: "Rejected", color: "#f87171" },
};
function getResearchBadge(research) {
    if (!research)
        return RESEARCH_BADGE.not_stored;
    if (research.graduated)
        return RESEARCH_BADGE.graduated;
    if (research.hypothesis?.status === "REJECTED")
        return RESEARCH_BADGE.rejected;
    if (research.hypothesis)
        return RESEARCH_BADGE.review;
    if (research.stored)
        return RESEARCH_BADGE.stored;
    return RESEARCH_BADGE.not_stored;
}
function ResearchActionsPanel({ research, prediction, actionPending, showCorrectForm, correctInput, showStoredEvidence, onApprove, onReject, onCorrectToggle, onCorrectInput, onCorrectSubmit, onToggleEvidence, }) {
    const badge = getResearchBadge(research);
    const hasHypothesis = !!research?.hypothesis;
    const evidenceCount = research?.evidence?.length ?? 0;
    return (_jsxs("div", { className: "subsection research-actions-section", children: [_jsxs("h3", { children: ["Research Status", _jsx("span", { className: "research-badge", style: { color: badge.color, borderColor: badge.color }, children: badge.label })] }), research && research.convergence_score > 0 && (_jsxs("div", { className: "research-convergence", children: [_jsx("div", { className: "convergence-meter", style: { height: 6 }, children: _jsx("div", { className: "convergence-fill", style: {
                                width: `${Math.min(research.convergence_score * 100, 100)}%`,
                                backgroundColor: (TIER_LABELS[research.tier] || TIER_LABELS[3]).color,
                            } }) }), _jsxs("span", { className: "research-conv-label", children: ["DB Convergence: ", (research.convergence_score * 100).toFixed(1), "%", research.disagreement_count > 0 && (_jsxs("span", { className: "disagree-flag", children: [" (", research.disagreement_count, " disagreements)"] }))] })] })), research?.proposed_function && (_jsxs("div", { className: "research-proposed-fn", children: [_jsx("span", { className: "fn-label", children: "Function:" }), " ", research.proposed_function] })), evidenceCount > 0 && (_jsxs("div", { className: "research-evidence-count", onClick: onToggleEvidence, style: { cursor: "pointer" }, children: [evidenceCount, " evidence record", evidenceCount !== 1 ? "s" : "", " in database", _jsx("span", { className: "toggle-icon", children: showStoredEvidence ? " ▾" : " ▸" })] })), showStoredEvidence && research?.evidence && (_jsx("div", { className: "stored-evidence-list", children: research.evidence.map((ev) => (_jsxs("div", { className: "stored-evidence-item", children: [_jsx("span", { className: "se-type", children: ev.evidence_type }), _jsx("span", { className: "se-ref", children: ev.source_ref || "—" }), ev.confidence != null && (_jsxs("span", { className: "se-conf", children: [(ev.confidence * 100).toFixed(0), "%"] }))] }, ev.evidence_id))) })), (hasHypothesis || prediction?.hypothesis) && !research?.graduated && (_jsxs("div", { className: "research-action-btns", children: [_jsx("button", { className: "research-btn approve-btn", onClick: onApprove, disabled: actionPending, children: "Approve" }), _jsx("button", { className: "research-btn reject-btn", onClick: onReject, disabled: actionPending, children: "Reject" }), _jsx("button", { className: "research-btn correct-btn", onClick: onCorrectToggle, disabled: actionPending, children: "Correct" })] })), showCorrectForm && (_jsxs("div", { className: "correct-form", children: [_jsx("input", { type: "text", className: "correct-input", placeholder: "Enter corrected function...", value: correctInput, onChange: (e) => onCorrectInput(e.target.value), onKeyDown: (e) => e.key === "Enter" && onCorrectSubmit() }), _jsx("button", { className: "research-btn approve-btn", onClick: onCorrectSubmit, disabled: actionPending || !correctInput.trim(), children: "Submit" })] }))] }));
}
function getAAClass(aa) {
    if ("DE".includes(aa))
        return "neg";
    if ("KRH".includes(aa))
        return "pos";
    if ("AILMFWVP".includes(aa))
        return "hydro";
    if ("STYCNQG".includes(aa))
        return "polar";
    return "other";
}
