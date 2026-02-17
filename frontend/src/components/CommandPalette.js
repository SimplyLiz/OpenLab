import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState, useEffect, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useGeneStore } from "../store";
import { usePipeline } from "../hooks/usePipeline";
export function CommandPalette() {
    const [open, setOpen] = useState(false);
    const [input, setInput] = useState("");
    const inputRef = useRef(null);
    const navigate = useNavigate();
    const { genome, isAnalyzing, setQuery, activeGenomeId } = useGeneStore();
    const { analyze } = usePipeline();
    // Cmd+K to toggle
    useEffect(() => {
        const handler = (e) => {
            if ((e.metaKey || e.ctrlKey) && e.key === "k") {
                e.preventDefault();
                setOpen((o) => !o);
            }
            if (e.key === "Escape") {
                setOpen(false);
            }
        };
        window.addEventListener("keydown", handler);
        return () => window.removeEventListener("keydown", handler);
    }, []);
    // Focus input when opened
    useEffect(() => {
        if (open)
            inputRef.current?.focus();
    }, [open]);
    const genes = genome?.genes ?? [];
    // Filter genes by input
    const filtered = input.trim()
        ? genes.filter((g) => g.locus_tag.toLowerCase().includes(input.toLowerCase()) ||
            g.gene_name.toLowerCase().includes(input.toLowerCase()) ||
            g.product.toLowerCase().includes(input.toLowerCase())).slice(0, 20)
        : [];
    const handleSubmit = (e) => {
        e.preventDefault();
        const q = input.trim();
        if (!q || isAnalyzing)
            return;
        setQuery(q);
        analyze(q);
        setOpen(false);
        setInput("");
    };
    const handleSelectGene = useCallback((locusTag) => {
        const gene = genes.find((g) => g.locus_tag === locusTag);
        if (gene) {
            useGeneStore.getState().selectGene(gene);
            if (activeGenomeId) {
                navigate(`/g/${activeGenomeId}/map`);
            }
        }
        setOpen(false);
        setInput("");
    }, [genes, activeGenomeId, navigate]);
    if (!open)
        return null;
    return (_jsx("div", { className: "command-palette-overlay", onClick: () => setOpen(false), children: _jsxs("div", { className: "command-palette", onClick: (e) => e.stopPropagation(), children: [_jsxs("form", { onSubmit: handleSubmit, className: "command-palette-form", children: [_jsx("span", { className: "command-palette-icon", children: _jsxs("svg", { width: "16", height: "16", viewBox: "0 0 16 16", fill: "none", stroke: "currentColor", strokeWidth: "1.5", children: [_jsx("circle", { cx: "7", cy: "7", r: "5" }), _jsx("line", { x1: "11", y1: "11", x2: "14", y2: "14" })] }) }), _jsx("input", { ref: inputRef, type: "text", value: input, onChange: (e) => setInput(e.target.value), placeholder: "Search genes, navigate, or analyze...", className: "command-palette-input" }), _jsx("kbd", { className: "command-palette-kbd", children: "esc" })] }), filtered.length > 0 && (_jsx("div", { className: "command-palette-results", children: filtered.map((g) => (_jsxs("button", { className: "command-palette-result", onClick: () => handleSelectGene(g.locus_tag), children: [_jsx("span", { className: "command-palette-result-tag", children: g.locus_tag }), _jsx("span", { className: "command-palette-result-name", children: g.gene_name || g.product || "Unknown" }), _jsx("span", { className: "command-palette-result-dot", style: { background: g.color } })] }, g.locus_tag))) })), input.trim() && filtered.length === 0 && (_jsx("div", { className: "command-palette-empty", children: _jsx("p", { children: "No matching genes. Press Enter to run a full analysis." }) }))] }) }));
}
