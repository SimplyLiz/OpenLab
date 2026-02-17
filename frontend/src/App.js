import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
import { Routes, Route, Navigate } from "react-router-dom";
import { AppShell } from "./components/AppShell";
import { CommandPalette } from "./components/CommandPalette";
import { PipelineStatus } from "./components/PipelineStatus";
import { GenomeSelectorPage } from "./pages/GenomeSelectorPage";
import { DashboardPage } from "./pages/DashboardPage";
import { PetriDishPage } from "./pages/PetriDishPage";
import { GenomeMapPage } from "./pages/GenomeMapPage";
import { ResearchPage } from "./pages/ResearchPage";
import { SimulationPage } from "./pages/SimulationPage";
import { GeneAnalysisPage } from "./pages/GeneAnalysisPage";
import { CellForgePage } from "./pages/CellForgePage";
import { SettingsPage } from "./pages/SettingsPage";
function RedirectToLastGenome() {
    return _jsx(Navigate, { to: "/genomes", replace: true });
}
export function App() {
    return (_jsxs(_Fragment, { children: [_jsx(CommandPalette, {}), _jsx(PipelineStatus, {}), _jsxs(Routes, { children: [_jsx(Route, { path: "/", element: _jsx(RedirectToLastGenome, {}) }), _jsx(Route, { path: "/genomes", element: _jsx(GenomeSelectorPage, {}) }), _jsxs(Route, { element: _jsx(AppShell, {}), children: [_jsx(Route, { path: "/g/:genomeId", element: _jsx(DashboardPage, {}) }), _jsx(Route, { path: "/g/:genomeId/petri", element: _jsx(PetriDishPage, {}) }), _jsx(Route, { path: "/g/:genomeId/map", element: _jsx(GenomeMapPage, {}) }), _jsx(Route, { path: "/g/:genomeId/research", element: _jsx(ResearchPage, {}) }), _jsx(Route, { path: "/g/:genomeId/simulation", element: _jsx(SimulationPage, {}) }), _jsx(Route, { path: "/g/:genomeId/cellforge", element: _jsx(CellForgePage, {}) })] }), _jsx(Route, { path: "/gene/:symbol", element: _jsx(GeneAnalysisPage, {}) }), _jsx(Route, { path: "/settings", element: _jsx(SettingsPage, {}) })] })] }));
}
