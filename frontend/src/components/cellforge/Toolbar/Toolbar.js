import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { SimControls } from './SimControls';
import { PerturbationPanel } from './PerturbationPanel';
export function Toolbar() {
    return (_jsxs("div", { style: { display: 'flex', flexDirection: 'column', gap: 8, padding: 8 }, children: [_jsx("h3", { children: "Controls" }), _jsx(SimControls, {}), _jsx(PerturbationPanel, {})] }));
}
