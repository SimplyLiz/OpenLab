import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { useGeneStore } from "../store";
import { CellSimulation } from "./CellSimulation";

export function AppShell() {
  const petriPiP = useGeneStore((s) => s.petriPiP);
  const genome = useGeneStore((s) => s.genome);

  return (
    <div className="app-shell">
      <Sidebar />
      <main className="app-main">
        <Outlet />
      </main>
      {petriPiP && genome && (
        <PiPContainer />
      )}
    </div>
  );
}

function PiPContainer() {
  const setPetriPiP = useGeneStore((s) => s.setPetriPiP);
  const activeGenomeId = useGeneStore((s) => s.activeGenomeId);

  const handleClick = () => {
    setPetriPiP(false);
    if (activeGenomeId) {
      window.location.href = `/g/${activeGenomeId}/petri`;
    }
  };

  return (
    <div className="pip-container" onClick={handleClick} title="Click to return to Petri Dish">
      <CellSimulation compact />
    </div>
  );
}
