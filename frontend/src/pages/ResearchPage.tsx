import { useParams } from "react-router-dom";
import { ResearchSidebar } from "../components/ResearchSidebar";
import { GeneDetail } from "../components/GeneDetail";
import { useGeneStore } from "../store";
import { useGenomeLoader } from "../hooks/useGenomes";

export function ResearchPage() {
  const { genomeId } = useParams();
  useGenomeLoader(genomeId);

  const genome = useGeneStore((s) => s.genome);
  const selectedGene = useGeneStore((s) => s.selectedGene);

  if (!genome) {
    return <div className="page-loading">Loading research...</div>;
  }

  return (
    <div className="page research-page">
      <ResearchSidebar />
      <div className="research-detail">
        {selectedGene ? (
          <GeneDetail />
        ) : (
          <div className="research-empty-state">
            <div className="research-empty-icon">&#x1F52C;</div>
            <p>Select a gene from the queue to view research details</p>
          </div>
        )}
      </div>
    </div>
  );
}
