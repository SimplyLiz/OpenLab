import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { MetaboliteChart } from './MetaboliteChart';
import { GeneExpressionHeatmap } from './GeneExpressionHeatmap';
import { FluxSankey } from './FluxSankey';
export function Dashboard() {
    return (_jsxs("div", { style: { display: 'flex', flexDirection: 'column', gap: 8, padding: 8 }, children: [_jsx("h3", { children: "Dashboard" }), _jsx(MetaboliteChart, {}), _jsx(GeneExpressionHeatmap, {}), _jsx(FluxSankey, {})] }));
}
