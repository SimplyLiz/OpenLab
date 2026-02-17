import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState, useCallback } from "react";
import { useGeneStore } from "../../store";
import { useKnockout } from "../../hooks/useKnockout";
export function KnockoutLab() {
    const genome = useGeneStore((s) => s.genome);
    const essentiality = useGeneStore((s) => s.essentiality);
    const knockoutSet = useGeneStore((s) => s.knockoutSet);
    const setKnockoutSet = useGeneStore((s) => s.setKnockoutSet);
    const { runKnockout, isRunning } = useKnockout();
    const [filter, setFilter] = useState("");
    // Get non-essential genes (candidates for knockout)
    const candidates = (genome?.genes ?? []).filter((g) => {
        if (essentiality?.predictions) {
            return essentiality.predictions[g.locus_tag] === false;
        }
        return true; // If no essentiality data, show all
    });
    const filtered = filter.trim()
        ? candidates.filter((g) => g.locus_tag.toLowerCase().includes(filter.toLowerCase()) ||
            g.gene_name.toLowerCase().includes(filter.toLowerCase()) ||
            g.product.toLowerCase().includes(filter.toLowerCase()))
        : candidates;
    const toggleGene = useCallback((locusTag) => {
        const next = new Set(knockoutSet);
        if (next.has(locusTag)) {
            next.delete(locusTag);
        }
        else {
            next.add(locusTag);
        }
        setKnockoutSet(next);
    }, [knockoutSet, setKnockoutSet]);
    const resetWT = useCallback(() => {
        setKnockoutSet(new Set());
        useGeneStore.getState().setKnockoutSimResult(null);
    }, [setKnockoutSet]);
    return (_jsxs("div", { className: "glass-panel knockout-lab", children: [_jsx("h3", { className: "glass-panel-title", children: "Knockout Lab" }), _jsx("input", { type: "text", className: "knockout-search", placeholder: "Filter genes...", value: filter, onChange: (e) => setFilter(e.target.value) }), _jsxs("div", { className: "knockout-list", children: [filtered.slice(0, 50).map((g) => (_jsxs("label", { className: "knockout-item", children: [_jsx("input", { type: "checkbox", checked: knockoutSet.has(g.locus_tag), onChange: () => toggleGene(g.locus_tag) }), _jsx("span", { className: "knockout-tag", children: g.locus_tag }), _jsx("span", { className: "knockout-name", children: g.gene_name || g.product || "" })] }, g.locus_tag))), filtered.length === 0 && (_jsx("div", { className: "knockout-empty", children: "No matching genes" }))] }), _jsxs("div", { className: "knockout-actions", children: [_jsx("button", { className: "knockout-btn knockout-run", onClick: runKnockout, disabled: knockoutSet.size === 0 || isRunning, children: isRunning ? "Simulating..." : `Run KO Sim (${knockoutSet.size})` }), _jsx("button", { className: "knockout-btn knockout-reset", onClick: resetWT, disabled: knockoutSet.size === 0 && !isRunning, children: "Reset WT" })] }), knockoutSet.size > 0 && (_jsxs("div", { className: "knockout-summary", children: [knockoutSet.size, " gene", knockoutSet.size !== 1 ? "s" : "", " knocked out"] }))] }));
}
