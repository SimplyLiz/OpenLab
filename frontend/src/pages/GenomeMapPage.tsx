import { useParams } from "react-router-dom";
import { GenomeCircle } from "../components/GenomeCircle";
import { GeneDetail } from "../components/GeneDetail";
import { GenomeOverview } from "../components/GenomeOverview";
import { useGeneStore } from "../store";
import { useGenomeLoader } from "../hooks/useGenomes";

export function GenomeMapPage() {
  const { genomeId } = useParams();
  useGenomeLoader(genomeId);

  const { genome, selectedGene } = useGeneStore();

  if (!genome) {
    return <div className="page-loading">Loading genome map...</div>;
  }

  return (
    <div className="page genome-map-page">
      <GenomeOverview />
      <div className={`genome-viz-grid ${selectedGene ? "gene-selected" : ""}`}>
        <div className="panel genome-circle-panel">
          <h2 className="panel-title">Genome Map</h2>
          <p className="panel-sub">Click a gene to inspect it. Red = unknown function.</p>
          <GenomeCircle />
        </div>
        {selectedGene && (
          <div className="right-stack">
            <GeneDetail />
          </div>
        )}
      </div>
    </div>
  );
}
