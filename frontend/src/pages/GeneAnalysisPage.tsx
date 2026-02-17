import { GeneOverview } from "../components/GeneOverview";
import { SequencePanel } from "../components/SequencePanel";
import { AnnotationPanel } from "../components/AnnotationPanel";
import { useGeneStore } from "../store";

export function GeneAnalysisPage() {
  const { geneRecord } = useGeneStore();

  if (!geneRecord) {
    return <div className="page-loading">No gene loaded. Use the search to analyze a gene.</div>;
  }

  return (
    <div className="page gene-analysis-page">
      <GeneOverview />
      <div className="analysis-grid">
        <SequencePanel />
        <AnnotationPanel />
      </div>
    </div>
  );
}
