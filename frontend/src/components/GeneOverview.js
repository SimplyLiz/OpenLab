import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useGeneStore } from "../store";
export function GeneOverview() {
    const { geneRecord } = useGeneStore();
    if (!geneRecord)
        return null;
    const { identifiers: ids, summary, aliases, sequences } = geneRecord;
    return (_jsxs("div", { className: "panel gene-overview", children: [_jsxs("h2", { className: "panel-title", children: [ids.symbol, _jsx("span", { className: "gene-name", children: ids.name })] }), _jsxs("div", { className: "id-grid", children: [ids.ncbi_gene_id && _jsx(IdTag, { label: "NCBI", value: ids.ncbi_gene_id }), ids.ensembl_gene && _jsx(IdTag, { label: "Ensembl", value: ids.ensembl_gene }), ids.uniprot_id && _jsx(IdTag, { label: "UniProt", value: ids.uniprot_id }), ids.refseq_mrna && _jsx(IdTag, { label: "RefSeq", value: ids.refseq_mrna }), ids.chromosome && _jsx(IdTag, { label: "Chr", value: ids.chromosome }), ids.map_location && _jsx(IdTag, { label: "Locus", value: ids.map_location })] }), aliases.length > 0 && (_jsxs("p", { className: "aliases", children: [_jsx("strong", { children: "Aliases:" }), " ", aliases.join(", ")] })), summary && _jsx("p", { className: "summary", children: summary }), _jsxs("div", { className: "sequences-summary", children: [_jsx("strong", { children: "Sequences loaded:" }), " ", sequences.map((s) => (_jsxs("span", { className: "seq-tag", children: [s.seq_type, " (", s.length.toLocaleString(), " ", s.seq_type === "protein" ? "aa" : "bp", ")"] }, s.accession || s.seq_type)))] })] }));
}
function IdTag({ label, value }) {
    return (_jsxs("div", { className: "id-tag", children: [_jsx("span", { className: "id-label", children: label }), _jsx("span", { className: "id-value", children: value })] }));
}
