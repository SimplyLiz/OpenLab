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
import { ResearchBookFeed } from "./pages/ResearchBookFeed";
import { ThreadDetailPage } from "./pages/ThreadDetailPage";
import { ForkPage } from "./pages/ForkPage";

function RedirectToLastGenome() {
  return <Navigate to="/genomes" replace />;
}

export function App() {
  return (
    <>
      <CommandPalette />
      <PipelineStatus />
      <Routes>
        <Route path="/" element={<RedirectToLastGenome />} />
        <Route path="/genomes" element={<GenomeSelectorPage />} />
        <Route element={<AppShell />}>
          <Route path="/g/:genomeId" element={<DashboardPage />} />
          <Route path="/g/:genomeId/petri" element={<PetriDishPage />} />
          <Route path="/g/:genomeId/map" element={<GenomeMapPage />} />
          <Route path="/g/:genomeId/research" element={<ResearchPage />} />
          <Route path="/g/:genomeId/simulation" element={<SimulationPage />} />
          <Route path="/g/:genomeId/cellforge" element={<CellForgePage />} />
        </Route>
        <Route path="/gene/:symbol" element={<GeneAnalysisPage />} />
        <Route path="/research" element={<ResearchBookFeed />} />
        <Route path="/research/:threadId" element={<ThreadDetailPage />} />
        <Route path="/research/:threadId/fork" element={<ForkPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Routes>
    </>
  );
}
