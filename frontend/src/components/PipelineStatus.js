import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useGeneStore } from "../store";
const STAGE_LABELS = {
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
const STATUS_ICONS = {
    pending: "\u25CB",
    running: "\u25D4",
    completed: "\u25CF",
    failed: "\u2717",
};
export function PipelineStatus() {
    const { stages, isAnalyzing, pipelinePhase, predictionProgress, kineticsProgress, simulationProgress, geneAnalysisStatus, geneAnalysisProgress, geneAnalysisMessage, } = useGeneStore();
    const stageEntries = Object.entries(stages).filter(([key]) => key !== "pipeline");
    if (stageEntries.length === 0 && !isAnalyzing && !geneAnalysisStatus) {
        return null;
    }
    // Compute overall pipeline progress
    const totalStages = stageEntries.length || 1;
    const completedStages = stageEntries.filter(([, s]) => s.status === "completed").length;
    const failedStages = stageEntries.filter(([, s]) => s.status === "failed").length;
    const overallPct = Math.round((completedStages / totalStages) * 100);
    const allDone = completedStages + failedStages === totalStages && totalStages > 1;
    return (_jsxs("div", { className: "pipeline-status", children: [_jsxs("div", { className: "pipeline-header", children: [_jsx("h3", { className: "pipeline-title", children: allDone ? "Pipeline Complete" : "Analysis Pipeline" }), !allDone && totalStages > 1 && (_jsxs("span", { className: "pipeline-overall", children: [completedStages, "/", totalStages, " stages \u2014 ", overallPct, "%"] }))] }), !allDone && totalStages > 1 && (_jsx("div", { className: "pipeline-progress-bar", children: _jsx("div", { className: "pipeline-progress-fill", style: { width: `${overallPct}%` } }) })), pipelinePhase && !allDone && (_jsx("div", { className: "pipeline-current-activity", children: pipelinePhase.message })), predictionProgress && !allDone && (_jsxs("div", { className: "pipeline-current-activity", children: ["Analyzed ", predictionProgress.analyzed, "/", predictionProgress.total, " unknown genes"] })), _jsx("div", { className: "pipeline-stages", children: stageEntries.map(([key, state]) => (_jsxs("div", { className: `stage-item stage-${state.status}`, children: [_jsx("span", { className: "stage-icon", children: STATUS_ICONS[state.status] }), _jsx("span", { className: "stage-label", children: STAGE_LABELS[key] ?? key }), state.status === "running" && key === "functional_prediction" && (_jsx("span", { className: "stage-progress-text", children: "analyzing..." })), state.status === "running" && key === "kinetics_enrichment" && kineticsProgress && (_jsxs("span", { className: "stage-progress-text", children: [kineticsProgress.done, "/", kineticsProgress.total, " (", kineticsProgress.measured_pct, "% measured)"] })), state.status === "running" && key === "simulation" && (_jsxs("span", { className: "stage-progress-text", children: [(simulationProgress * 100).toFixed(0), "%"] })), state.status === "running" && key === "gene_analysis" && (_jsxs("span", { className: "stage-progress-text", children: [(geneAnalysisProgress * 100).toFixed(0), "%"] })), state.error && _jsx("span", { className: "stage-error", title: state.error, children: "error" })] }, key))) }), geneAnalysisStatus === "running" && geneAnalysisMessage && (_jsx("div", { className: "pipeline-current-activity", style: { marginTop: "0.5rem" }, children: geneAnalysisMessage }))] }));
}
