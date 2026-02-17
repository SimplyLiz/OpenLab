import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useCallback } from "react";
import { NavLink, useParams } from "react-router-dom";
import { useGeneStore } from "../store";
const API = `${location.protocol}//${location.host}/api/v1`;
const NAV_ITEMS = [
    {
        path: "",
        label: "Dashboard",
        icon: (_jsxs("svg", { width: "20", height: "20", viewBox: "0 0 20 20", fill: "none", stroke: "currentColor", strokeWidth: "1.5", children: [_jsx("rect", { x: "2", y: "2", width: "7", height: "7", rx: "1" }), _jsx("rect", { x: "11", y: "2", width: "7", height: "7", rx: "1" }), _jsx("rect", { x: "2", y: "11", width: "7", height: "7", rx: "1" }), _jsx("rect", { x: "11", y: "11", width: "7", height: "7", rx: "1" })] })),
    },
    {
        path: "/petri",
        label: "Petri Dish",
        icon: (_jsxs("svg", { width: "20", height: "20", viewBox: "0 0 20 20", fill: "none", stroke: "currentColor", strokeWidth: "1.5", children: [_jsx("circle", { cx: "10", cy: "10", r: "8" }), _jsx("circle", { cx: "7", cy: "8", r: "1.5", fill: "currentColor", opacity: "0.4" }), _jsx("circle", { cx: "12", cy: "11", r: "1", fill: "currentColor", opacity: "0.4" }), _jsx("circle", { cx: "10", cy: "7", r: "0.8", fill: "currentColor", opacity: "0.4" })] })),
    },
    {
        path: "/map",
        label: "Genome Map",
        icon: (_jsxs("svg", { width: "20", height: "20", viewBox: "0 0 20 20", fill: "none", stroke: "currentColor", strokeWidth: "1.5", children: [_jsx("circle", { cx: "10", cy: "10", r: "7" }), _jsx("circle", { cx: "10", cy: "10", r: "3", strokeDasharray: "2 2" })] })),
    },
    {
        path: "/research",
        label: "Research",
        icon: (_jsxs("svg", { width: "20", height: "20", viewBox: "0 0 20 20", fill: "none", stroke: "currentColor", strokeWidth: "1.5", children: [_jsx("path", { d: "M8 2v6l-2 4h8l-2-4V2" }), _jsx("path", { d: "M5 12h10v2a4 4 0 01-4 4H9a4 4 0 01-4-4v-2z" }), _jsx("line", { x1: "6", y1: "2", x2: "14", y2: "2" })] })),
    },
    {
        path: "/simulation",
        label: "Simulation",
        icon: (_jsxs("svg", { width: "20", height: "20", viewBox: "0 0 20 20", fill: "none", stroke: "currentColor", strokeWidth: "1.5", children: [_jsx("polyline", { points: "2,16 6,10 10,13 14,5 18,8" }), _jsx("line", { x1: "2", y1: "18", x2: "18", y2: "18" })] })),
    },
    {
        path: "/cellforge",
        label: "CellForge 3D",
        icon: (_jsxs("svg", { width: "20", height: "20", viewBox: "0 0 20 20", fill: "none", stroke: "currentColor", strokeWidth: "1.5", children: [_jsx("ellipse", { cx: "10", cy: "10", rx: "8", ry: "5" }), _jsx("ellipse", { cx: "10", cy: "10", rx: "8", ry: "5", transform: "rotate(60 10 10)" }), _jsx("ellipse", { cx: "10", cy: "10", rx: "8", ry: "5", transform: "rotate(120 10 10)" }), _jsx("circle", { cx: "10", cy: "10", r: "1.5", fill: "currentColor" })] })),
    },
];
export function Sidebar() {
    const { genomeId } = useParams();
    const genomes = useGeneStore((s) => s.genomes);
    const setGenomes = useGeneStore((s) => s.setGenomes);
    const activeGenomeId = useGeneStore((s) => s.activeGenomeId);
    const fetchGenomes = useCallback(async () => {
        try {
            const res = await fetch(`${API}/genomes`);
            if (res.ok) {
                const data = await res.json();
                setGenomes(data);
            }
        }
        catch { /* silent */ }
    }, [setGenomes]);
    useEffect(() => {
        if (genomes.length === 0)
            fetchGenomes();
    }, [genomes.length, fetchGenomes]);
    const basePath = genomeId ? `/g/${genomeId}` : activeGenomeId ? `/g/${activeGenomeId}` : "";
    return (_jsxs("nav", { className: "sidebar", children: [_jsx("div", { className: "sidebar-logo", children: _jsxs(NavLink, { to: "/", className: "sidebar-logo-link", children: [_jsx("span", { className: "logo-gene", children: "G" }), _jsx("span", { className: "logo-life", children: "L" })] }) }), _jsx("div", { className: "sidebar-nav", children: basePath &&
                    NAV_ITEMS.map((item) => (_jsxs(NavLink, { to: `${basePath}${item.path}`, end: item.path === "", className: ({ isActive }) => `sidebar-item ${isActive ? "sidebar-item-active" : ""}`, title: item.label, children: [_jsx("span", { className: "sidebar-icon", children: item.icon }), _jsx("span", { className: "sidebar-label", children: item.label })] }, item.path))) }), _jsxs("div", { className: "sidebar-footer", children: [_jsxs(NavLink, { to: "/genomes", className: "sidebar-item sidebar-genome-picker", title: "Switch Genome", children: [_jsx("span", { className: "sidebar-icon", children: _jsxs("svg", { width: "20", height: "20", viewBox: "0 0 20 20", fill: "none", stroke: "currentColor", strokeWidth: "1.5", children: [_jsx("path", { d: "M3 7l7-5 7 5-7 5z" }), _jsx("path", { d: "M3 13l7 5 7-5" }), _jsx("path", { d: "M3 10l7 5 7-5" })] }) }), _jsx("span", { className: "sidebar-label", children: "Genomes" })] }), _jsxs(NavLink, { to: "/settings", className: "sidebar-item sidebar-settings-link", title: "AI Settings", children: [_jsx("span", { className: "sidebar-icon", children: _jsxs("svg", { width: "20", height: "20", viewBox: "0 0 20 20", fill: "none", stroke: "currentColor", strokeWidth: "1.5", children: [_jsx("circle", { cx: "10", cy: "10", r: "3" }), _jsx("path", { d: "M10 1v3M10 16v3M1 10h3M16 10h3M3.5 3.5l2.1 2.1M14.4 14.4l2.1 2.1M16.5 3.5l-2.1 2.1M5.6 14.4l-2.1 2.1" })] }) }), _jsx("span", { className: "sidebar-label", children: "AI Settings" })] })] })] }));
}
