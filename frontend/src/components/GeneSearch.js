import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from "react";
import { useGeneStore } from "../store";
import { usePipeline } from "../hooks/usePipeline";
const GENE_EXAMPLES = ["TP53", "BRCA1", "CFTR", "EGFR"];
const GENOME_EXAMPLES = ["JCVI-syn3.0", "JCVI-syn2.0", "JCVI-syn3A"];
export function GeneSearch() {
    const [input, setInput] = useState("");
    const { isAnalyzing, setQuery } = useGeneStore();
    const { analyze } = usePipeline();
    const handleSubmit = (e) => {
        e.preventDefault();
        const q = input.trim();
        if (!q || isAnalyzing)
            return;
        setQuery(q);
        analyze(q);
    };
    const handleExample = (gene) => {
        setInput(gene);
        setQuery(gene);
        analyze(gene);
    };
    return (_jsxs("div", { className: "gene-search", children: [_jsxs("h1", { className: "logo", children: [_jsx("span", { className: "logo-gene", children: "Gene" }), _jsx("span", { className: "logo-life", children: "Life" })] }), _jsx("p", { className: "tagline", children: "Drop in a gene. Understand it completely. Bring it to life." }), _jsxs("form", { onSubmit: handleSubmit, className: "search-form", children: [_jsx("input", { type: "text", value: input, onChange: (e) => setInput(e.target.value), placeholder: "Gene symbol, genome accession, or organism (e.g. TP53, JCVI-syn3.0)", className: "search-input", disabled: isAnalyzing, autoFocus: true }), _jsx("button", { type: "submit", className: "search-btn", disabled: isAnalyzing || !input.trim(), children: isAnalyzing ? "Analyzing..." : "Analyze" })] }), _jsxs("div", { className: "examples", children: [_jsx("span", { className: "examples-label", children: "Genes:" }), GENE_EXAMPLES.map((gene) => (_jsx("button", { className: "example-chip", onClick: () => handleExample(gene), disabled: isAnalyzing, children: gene }, gene))), _jsx("span", { className: "examples-label", style: { marginLeft: "0.75rem" }, children: "Synthetic Genomes:" }), GENOME_EXAMPLES.map((gene) => (_jsx("button", { className: "example-chip genome-chip", onClick: () => handleExample(gene), disabled: isAnalyzing, children: gene }, gene)))] })] }));
}
