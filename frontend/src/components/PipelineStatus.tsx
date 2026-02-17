import { useGeneStore } from "../store";
import type { StageStatus } from "../types";

const STAGE_LABELS: Record<string, string> = {
  ingest: "Gene Identification",
  sequence_analysis: "Sequence Analysis",
  annotation: "Annotation & Function",
  genome_ingest: "Genome Fetch & Parse",
  functional_prediction: "Mystery Gene Analysis",
  genome_updated: "Results Ready",
  essentiality_prediction: "Essentiality",
  kinetics_enrichment: "Kinetics",
  cellspec_assembly: "CellSpec",
  simulation: "Simulation",
  validation: "Validation",
  gene_analysis: "Deep Gene Analysis",
};

const STATUS_ICONS: Record<StageStatus, string> = {
  pending: "\u25CB",
  running: "\u25D4",
  completed: "\u25CF",
  failed: "\u2717",
};

export function PipelineStatus() {
  const {
    stages, isAnalyzing,
    pipelinePhase, predictionProgress, kineticsProgress,
    simulationProgress,
    geneAnalysisStatus, geneAnalysisProgress, geneAnalysisMessage,
  } = useGeneStore();

  const stageEntries = Object.entries(stages).filter(
    ([key]) => key !== "pipeline"
  );
  if (stageEntries.length === 0 && !isAnalyzing && !geneAnalysisStatus) {
    return null;
  }

  // Compute overall pipeline progress
  const totalStages = stageEntries.length || 1;
  const completedStages = stageEntries.filter(([, s]) => s.status === "completed").length;
  const failedStages = stageEntries.filter(([, s]) => s.status === "failed").length;
  const overallPct = Math.round((completedStages / totalStages) * 100);
  const allDone = completedStages + failedStages === totalStages && totalStages > 1;

  return (
    <div className="pipeline-status">
      <div className="pipeline-header">
        <h3 className="pipeline-title">
          {allDone ? "Pipeline Complete" : "Analysis Pipeline"}
        </h3>
        {!allDone && totalStages > 1 && (
          <span className="pipeline-overall">
            {completedStages}/{totalStages} stages — {overallPct}%
          </span>
        )}
      </div>

      {/* Overall progress bar */}
      {!allDone && totalStages > 1 && (
        <div className="pipeline-progress-bar">
          <div
            className="pipeline-progress-fill"
            style={{ width: `${overallPct}%` }}
          />
        </div>
      )}

      {/* Current activity detail */}
      {pipelinePhase && !allDone && (
        <div className="pipeline-current-activity">
          {pipelinePhase.message}
        </div>
      )}
      {predictionProgress && !allDone && (
        <div className="pipeline-current-activity">
          Analyzed {predictionProgress.analyzed}/{predictionProgress.total} unknown genes
        </div>
      )}

      <div className="pipeline-stages">
        {stageEntries.map(([key, state]) => (
          <div key={key} className={`stage-item stage-${state.status}`}>
            <span className="stage-icon">{STATUS_ICONS[state.status]}</span>
            <span className="stage-label">{STAGE_LABELS[key] ?? key}</span>
            {state.status === "running" && key === "functional_prediction" && (
              <span className="stage-progress-text">analyzing...</span>
            )}
            {state.status === "running" && key === "kinetics_enrichment" && kineticsProgress && (
              <span className="stage-progress-text">
                {kineticsProgress.done}/{kineticsProgress.total} ({kineticsProgress.measured_pct}% measured)
              </span>
            )}
            {state.status === "running" && key === "simulation" && (
              <span className="stage-progress-text">
                {(simulationProgress * 100).toFixed(0)}%
              </span>
            )}
            {state.status === "running" && key === "gene_analysis" && (
              <span className="stage-progress-text">
                {(geneAnalysisProgress * 100).toFixed(0)}%
              </span>
            )}
            {state.error && <span className="stage-error" title={state.error}>error</span>}
          </div>
        ))}
      </div>

      {/* Gene analysis detail (below stages when active) */}
      {geneAnalysisStatus === "running" && geneAnalysisMessage && (
        <div className="pipeline-current-activity" style={{ marginTop: "0.5rem" }}>
          {geneAnalysisMessage}
        </div>
      )}
    </div>
  );
}
