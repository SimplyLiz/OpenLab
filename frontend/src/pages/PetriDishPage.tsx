import { useEffect } from "react";
import { useParams } from "react-router-dom";
import { useGeneStore } from "../store";
import { useGenomeLoader } from "../hooks/useGenomes";
import { CellSimulation } from "../components/CellSimulation";
import { KnockoutLab } from "../components/petri/KnockoutLab";
import { MetricsOverlay } from "../components/petri/MetricsOverlay";
import { PlaybackBar } from "../components/petri/PlaybackBar";

export function PetriDishPage() {
  const { genomeId } = useParams();
  useGenomeLoader(genomeId);

  const genome = useGeneStore((s) => s.genome);
  const setPetriPiP = useGeneStore((s) => s.setPetriPiP);

  // When entering Petri Dish, disable PiP
  useEffect(() => {
    setPetriPiP(false);
    return () => {
      // When leaving, enable PiP
      setPetriPiP(true);
    };
  }, [setPetriPiP]);

  if (!genome) {
    return <div className="page-loading">Loading Petri Dish...</div>;
  }

  return (
    <div className="petri-dish-page">
      {/* Full-bleed canvas */}
      <div className="petri-canvas-container">
        <CellSimulation />
      </div>

      {/* Floating overlay panels */}
      <div className="petri-overlay">
        {/* Top bar */}
        <div className="petri-top-bar">
          <div className="petri-genome-badge">
            <span className="petri-badge-accession">{genome.accession}</span>
            <span className="petri-badge-organism">{genome.organism}</span>
          </div>
        </div>

        {/* Bottom panels */}
        <div className="petri-bottom-panels">
          <KnockoutLab />
          <div className="petri-spacer" />
          <MetricsOverlay />
        </div>

        {/* Playback bar */}
        <PlaybackBar />
      </div>
    </div>
  );
}
