import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
export function GeneDetail({ geneId, product, mrna, protein, isKO }) {
    return (_jsxs("div", { style: {
            marginTop: 4,
            padding: 6,
            background: '#1a1a2a',
            borderRadius: 4,
            fontSize: 11,
            color: '#ccc',
        }, children: [_jsxs("div", { style: { display: 'flex', justifyContent: 'space-between', marginBottom: 2 }, children: [_jsx("b", { style: { color: isKO ? '#f66' : '#fff' }, children: geneId }), isKO && _jsx("span", { style: { color: '#f66', fontSize: 10 }, children: "KNOCKED OUT" })] }), _jsx("div", { style: { color: '#888' }, children: product }), _jsxs("div", { style: { display: 'flex', gap: 16, marginTop: 4 }, children: [_jsxs("span", { children: ["mRNA: ", _jsx("b", { style: { color: '#4af' }, children: mrna })] }), _jsxs("span", { children: ["Protein: ", _jsx("b", { style: { color: '#f84' }, children: protein })] })] })] }));
}
