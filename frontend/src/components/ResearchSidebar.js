import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState, useEffect, useRef } from "react";
import { useGeneStore } from "../store";
import { useResearchManager } from "../hooks/useAutoResearch";
import { useResearch } from "../hooks/useResearch";
export function ResearchSidebar() {
    const { genome, selectGene, geneAnalysisStatus, geneAnalysisTarget } = useGeneStore();
    const { queue, totalQueued, queueLoading, refetchQueue, batchActive, batchCurrentGene, batchCompleted, batchTotal, batchProgress, startBatchResearch, stopBatchResearch, researchSingleGene, } = useResearchManager();
    const { fetchSummary } = useResearch();
    const [summary, setSummary] = useState(null);
    const [tab, setTab] = useState("queue");
    const prevBatchActive = useRef(batchActive);
    // Fetch summary on mount
    useEffect(() => {
        fetchSummary().then((s) => {
            if (s)
                setSummary(s);
        });
    }, [fetchSummary]);
    // Refetch summary + queue when batch finishes
    useEffect(() => {
        if (prevBatchActive.current && !batchActive) {
            fetchSummary().then((s) => {
                if (s)
                    setSummary(s);
            });
            refetchQueue();
        }
        prevBatchActive.current = batchActive;
    }, [batchActive, fetchSummary, refetchQueue]);
    const handleClickGene = (locusTag) => {
        if (!genome)
            return;
        const g = genome.genes.find((gene) => gene.locus_tag === locusTag);
        if (g)
            selectGene(g);
    };
    const batchPct = Math.round(batchProgress * 100);
    return (_jsxs("aside", { className: "research-sidebar", children: [_jsx("h2", { className: "sidebar-title", children: "Research" }), summary && (_jsxs("div", { className: "sidebar-summary", children: [_jsxs("div", { className: "sidebar-stat", children: [_jsx("div", { className: "sidebar-stat-num", children: summary.total_stored }), _jsx("div", { className: "sidebar-stat-label", children: "stored" })] }), _jsxs("div", { className: "sidebar-stat", children: [_jsx("div", { className: "sidebar-stat-num", style: { color: "#60a5fa" }, children: summary.total_with_evidence }), _jsx("div", { className: "sidebar-stat-label", children: "evidence" })] }), _jsxs("div", { className: "sidebar-stat", children: [_jsx("div", { className: "sidebar-stat-num", style: { color: "#fbbf24" }, children: summary.total_with_hypothesis }), _jsx("div", { className: "sidebar-stat-label", children: "hypothesized" })] }), _jsxs("div", { className: "sidebar-stat", children: [_jsx("div", { className: "sidebar-stat-num", style: { color: "#34d399" }, children: summary.total_graduated }), _jsx("div", { className: "sidebar-stat-label", children: "graduated" })] }), _jsxs("div", { className: "sidebar-stat", children: [_jsx("div", { className: "sidebar-stat-num", style: { color: "#f87171" }, children: summary.total_unknown }), _jsx("div", { className: "sidebar-stat-label", children: "unknown" })] }), _jsxs("div", { className: "sidebar-stat", children: [_jsx("div", { className: "sidebar-stat-num", style: { color: "#a78bfa" }, children: totalQueued }), _jsx("div", { className: "sidebar-stat-label", children: "queued" })] })] })), !batchActive && totalQueued > 0 && (_jsxs("button", { className: "batch-research-btn", onClick: startBatchResearch, children: ["Research All Unknown (", totalQueued, ")"] })), batchActive && (_jsxs("div", { className: "batch-progress", children: [batchCurrentGene && (_jsxs("div", { className: "batch-status", children: ["Analyzing ", batchCurrentGene] })), _jsx("div", { className: "arb-track", children: _jsx("div", { className: "arb-fill", style: { width: `${batchPct}%` } }) }), _jsxs("div", { className: "batch-status", children: [batchCompleted, " / ", batchTotal, " completed (", batchPct, "%)"] }), _jsx("button", { className: "cancel-batch-btn", onClick: stopBatchResearch, children: "Cancel" })] })), _jsxs("div", { className: "sidebar-tabs", children: [_jsxs("button", { className: `sidebar-tab ${tab === "queue" ? "active" : ""}`, onClick: () => setTab("queue"), children: ["Queue", totalQueued > 0 ? ` (${totalQueued})` : ""] }), _jsxs("button", { className: `sidebar-tab ${tab === "review" ? "active" : ""}`, onClick: () => setTab("review"), children: ["Review", summary ? ` (${summary.needs_review.length})` : ""] }), _jsxs("button", { className: `sidebar-tab ${tab === "candidates" ? "active" : ""}`, onClick: () => setTab("candidates"), children: ["Grads", summary ? ` (${summary.graduation_candidates.length})` : ""] }), _jsxs("button", { className: `sidebar-tab ${tab === "disagreements" ? "active" : ""}`, onClick: () => setTab("disagreements"), children: ["Conflicts", summary ? ` (${summary.disagreements.length})` : ""] })] }), tab === "queue" && (_jsxs("div", { className: "queue-list", children: [queueLoading && _jsx("p", { className: "text-dim", children: "Loading queue..." }), !queueLoading && queue.length === 0 && (_jsx("p", { className: "text-dim", children: "No unknown genes in queue" })), queue.map((item) => {
                        const isRunning = geneAnalysisTarget === item.locus_tag &&
                            geneAnalysisStatus === "running";
                        return (_jsxs("div", { className: "queue-item", children: [_jsx("span", { className: "queue-item-tag", onClick: () => handleClickGene(item.locus_tag), children: item.locus_tag }), _jsx("button", { className: "queue-analyze-btn", disabled: batchActive || geneAnalysisStatus === "running", onClick: () => {
                                        handleClickGene(item.locus_tag);
                                        researchSingleGene(item.locus_tag);
                                    }, children: isRunning ? "..." : "Analyze" })] }, item.locus_tag));
                    })] })), tab === "review" && (_jsx("div", { className: "research-list", children: !summary || summary.needs_review.length === 0 ? (_jsx("p", { className: "text-dim", children: "No genes with DRAFT hypotheses" })) : (summary.needs_review.map((item) => (_jsxs("div", { className: "research-list-item", onClick: () => handleClickGene(item.locus_tag), children: [_jsx("span", { className: "rli-tag", children: item.locus_tag }), _jsx("span", { className: "rli-title", children: item.hypothesis_title }), _jsxs("span", { className: "rli-conf", children: [((item.confidence ?? 0) * 100).toFixed(0), "%"] })] }, item.locus_tag)))) })), tab === "candidates" && (_jsx("div", { className: "research-list", children: !summary || summary.graduation_candidates.length === 0 ? (_jsx("p", { className: "text-dim", children: "No graduation candidates yet" })) : (summary.graduation_candidates.map((item) => (_jsxs("div", { className: "research-list-item", onClick: () => handleClickGene(item.locus_tag), children: [_jsx("span", { className: "rli-tag", children: item.locus_tag }), _jsx("span", { className: "rli-title", children: item.proposed_function }), _jsxs("span", { className: "rli-conf", style: { color: "#34d399" }, children: [((item.confidence ?? 0) * 100).toFixed(0), "%"] })] }, item.locus_tag)))) })), tab === "disagreements" && (_jsx("div", { className: "research-list", children: !summary || summary.disagreements.length === 0 ? (_jsx("p", { className: "text-dim", children: "No evidence disagreements detected" })) : (summary.disagreements.map((item) => (_jsxs("div", { className: "research-list-item", onClick: () => handleClickGene(item.locus_tag), children: [_jsx("span", { className: "rli-tag", children: item.locus_tag }), _jsx("span", { className: "rli-title", style: { color: "#f87171" }, children: item.top_disagreement }), _jsxs("span", { className: "rli-conf", children: [item.disagreement_count, " conflict", item.disagreement_count !== 1 ? "s" : ""] })] }, item.locus_tag)))) }))] }));
}
