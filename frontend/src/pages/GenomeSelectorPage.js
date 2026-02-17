import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useState, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useGenomes } from "../hooks/useGenomes";
export function GenomeSelectorPage() {
    const navigate = useNavigate();
    const { genomes, fetchGenomes, selectGenome, searchNCBI, fetchGenome } = useGenomes();
    const [searchQuery, setSearchQuery] = useState("");
    const [searchResults, setSearchResults] = useState([]);
    const [searching, setSearching] = useState(false);
    const [importing, setImporting] = useState(null);
    const [error, setError] = useState(null);
    const debounceRef = useRef(null);
    useEffect(() => {
        fetchGenomes();
    }, [fetchGenomes]);
    const handleSearch = useCallback((query) => {
        setSearchQuery(query);
        setError(null);
        if (debounceRef.current)
            clearTimeout(debounceRef.current);
        if (query.length < 2) {
            setSearchResults([]);
            setSearching(false);
            return;
        }
        setSearching(true);
        debounceRef.current = setTimeout(async () => {
            try {
                const results = await searchNCBI(query);
                setSearchResults(results);
            }
            catch {
                setSearchResults([]);
            }
            finally {
                setSearching(false);
            }
        }, 300);
    }, [searchNCBI]);
    const handleImport = async (accession) => {
        setImporting(accession);
        setError(null);
        try {
            const result = await fetchGenome(accession);
            await fetchGenomes();
            if (result.genome_id) {
                selectGenome(result.genome_id);
            }
        }
        catch (err) {
            setError(`Import failed for ${accession}`);
        }
        finally {
            setImporting(null);
        }
    };
    const fmtBp = (n) => {
        if (n >= 1_000_000)
            return `${(n / 1_000_000).toFixed(2)} Mbp`;
        if (n >= 1_000)
            return `${(n / 1_000).toFixed(1)} kbp`;
        return `${n} bp`;
    };
    return (_jsxs("div", { className: "genome-selector-page", children: [_jsxs("header", { className: "genome-selector-header", children: [_jsxs("h1", { className: "logo", children: [_jsx("span", { className: "logo-gene", children: "Gene" }), _jsx("span", { className: "logo-life", children: "Life" })] }), _jsx("p", { className: "genome-selector-tagline", children: "Select a genome to explore" })] }), _jsxs("div", { className: "genome-card-grid", children: [genomes.map((g) => (_jsxs("button", { className: "genome-card", onClick: () => selectGenome(g.genome_id), children: [_jsx("div", { className: "genome-card-accession", children: g.accession }), _jsx("div", { className: "genome-card-organism", children: g.organism }), _jsxs("div", { className: "genome-card-stats", children: [_jsx("span", { children: fmtBp(g.genome_length) }), _jsxs("span", { children: [g.total_genes, " genes"] }), g.gc_content != null && _jsxs("span", { children: ["GC ", g.gc_content.toFixed(1), "%"] })] }), _jsxs("div", { className: "genome-card-badges", children: [g.is_circular && _jsx("span", { className: "genome-badge circular", children: "circular" }), g.genes_unknown > 0 && (_jsxs("span", { className: "genome-badge unknown", children: [g.genes_unknown, " unknown"] }))] })] }, g.genome_id))), _jsxs("div", { className: "genome-card genome-search-card", children: [_jsx("div", { className: "genome-search-header", children: "Search NCBI" }), _jsx("input", { className: "genome-search-input", type: "text", placeholder: "Search NCBI (e.g. mycoplasma)", value: searchQuery, onChange: (e) => handleSearch(e.target.value) }), searching && _jsx("div", { className: "genome-search-spinner", children: "Searching..." }), error && _jsx("div", { className: "genome-search-error", children: error }), searchResults.length > 0 && (_jsx("div", { className: "genome-search-results", children: searchResults.map((r) => (_jsxs("div", { className: "genome-search-row", children: [_jsxs("div", { className: "genome-search-row-info", children: [_jsx("div", { className: "genome-search-row-organism", children: r.organism }), _jsxs("div", { className: "genome-search-row-meta", children: [_jsx("span", { children: r.accession }), _jsx("span", { children: fmtBp(r.length) })] })] }), _jsx("button", { className: "genome-search-import-btn", disabled: importing !== null, onClick: () => handleImport(r.accession), children: importing === r.accession ? "Importing..." : "Import" })] }, r.accession))) }))] })] }), genomes.length === 0 && !searchResults.length && (_jsx("div", { className: "genome-selector-empty", children: _jsx("p", { children: "No genomes yet. Search NCBI to import your first genome." }) }))] }));
}
