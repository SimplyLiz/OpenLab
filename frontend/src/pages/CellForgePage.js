import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { PetriDish } from '@/components/cellforge/PetriDish/PetriDish';
import { Dashboard } from '@/components/cellforge/Dashboard/Dashboard';
import { Toolbar } from '@/components/cellforge/Toolbar/Toolbar';
import { GenomeBrowser } from '@/components/cellforge/GenomeBrowser/GenomeBrowser';
export function CellForgePage() {
    return (_jsxs("div", { style: { display: 'flex', height: 'calc(100vh - 3rem)', background: '#111', color: '#eee' }, children: [_jsx("div", { style: { width: 280, borderRight: '1px solid #333', overflow: 'auto' }, children: _jsx(Toolbar, {}) }), _jsxs("div", { style: { flex: 1, display: 'flex', flexDirection: 'column' }, children: [_jsx("div", { style: { flex: 1 }, children: _jsx(PetriDish, {}) }), _jsx("div", { style: { height: 180, borderTop: '1px solid #333', overflow: 'auto' }, children: _jsx(GenomeBrowser, {}) })] }), _jsx("div", { style: { width: 360, borderLeft: '1px solid #333', overflow: 'auto' }, children: _jsx(Dashboard, {}) })] }));
}
