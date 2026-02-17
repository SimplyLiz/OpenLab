import { useParams } from "react-router-dom";
import { SimulationDashboard } from "../components/SimulationDashboard";
import { CellSimulation } from "../components/CellSimulation";
import { useGeneStore } from "../store";
import { useGenomeLoader } from "../hooks/useGenomes";

export function SimulationPage() {
  const { genomeId } = useParams();
  useGenomeLoader(genomeId);

  const genome = useGeneStore((s) => s.genome);

  if (!genome) {
    return <div className="page-loading">Loading simulation...</div>;
  }

  return (
    <div className="page simulation-page">
      <div className="panel cell-sim-panel">
        <h2 className="panel-title">Virtual Cell</h2>
        <p className="panel-sub">Minimal synthetic cell — alive on screen</p>
        <CellSimulation />
      </div>
      <SimulationDashboard />
    </div>
  );
}
