import { create } from "zustand";
import { simulationBuffer } from "./utils/simulationBuffer";
export const useGeneStore = create((set) => ({
    query: "",
    setQuery: (q) => set({ query: q }),
    mode: null,
    activeGenomeId: null,
    genomes: [],
    setActiveGenomeId: (id) => set({ activeGenomeId: id }),
    setGenomes: (g) => set({ genomes: g }),
    knockoutSet: new Set(),
    knockoutSimResult: null,
    setKnockoutSet: (s) => set({ knockoutSet: s }),
    setKnockoutSimResult: (r) => set({ knockoutSimResult: r }),
    petriPiP: false,
    setPetriPiP: (v) => set({ petriPiP: v }),
    isAnalyzing: false,
    stages: {},
    geneRecord: null,
    sequenceAnalysis: null,
    annotation: null,
    genome: null,
    selectedGene: null,
    predictionProgress: null,
    pipelinePhase: null,
    functionalAnalysis: null,
    predictions: new Map(),
    essentiality: null,
    kinetics: null,
    kineticsProgress: null,
    cellSpec: null,
    simulationSnapshots: [],
    simulationProgress: 0,
    simulationWallTime: 0,
    simulationResult: null,
    validation: null,
    geneAnalysisStatus: null,
    geneAnalysisProgress: 0,
    geneAnalysisMessage: "",
    geneAnalysisTarget: null,
    researchStatus: new Map(),
    startAnalysis: () => {
        simulationBuffer.clear();
        set({
            isAnalyzing: true,
            mode: null,
            stages: {},
            geneRecord: null,
            sequenceAnalysis: null,
            annotation: null,
            genome: null,
            selectedGene: null,
            predictionProgress: null,
            pipelinePhase: null,
            functionalAnalysis: null,
            predictions: new Map(),
            essentiality: null,
            kinetics: null,
            kineticsProgress: null,
            cellSpec: null,
            simulationSnapshots: [],
            simulationProgress: 0,
            simulationWallTime: 0,
            simulationResult: null,
            validation: null,
        });
    },
    startGeneAnalysis: (locus_tag) => set({
        geneAnalysisStatus: "running",
        geneAnalysisProgress: 0,
        geneAnalysisMessage: "Starting deep analysis...",
        geneAnalysisTarget: locus_tag,
    }),
    handleEvent: (event) => set((state) => {
        const newStages = { ...state.stages };
        newStages[event.stage] = {
            status: event.status,
            data: event.data,
            error: event.error,
        };
        const updates = { stages: newStages };
        if (event.status === "completed" && event.data) {
            switch (event.stage) {
                // Single gene mode
                case "ingest":
                    updates.mode = "gene";
                    updates.geneRecord = event.data;
                    break;
                case "sequence_analysis":
                    updates.sequenceAnalysis = event.data;
                    break;
                case "annotation":
                    updates.annotation = event.data;
                    break;
                // Genome mode
                case "genome_ingest":
                    updates.mode = "genome";
                    updates.genome = event.data;
                    break;
                case "genome_updated":
                    updates.genome = event.data;
                    break;
                case "functional_prediction": {
                    const analysis = event.data;
                    updates.functionalAnalysis = analysis;
                    if (analysis?.predictions) {
                        const pMap = new Map();
                        for (const pred of analysis.predictions) {
                            pMap.set(pred.locus_tag, pred);
                        }
                        updates.predictions = pMap;
                    }
                    break;
                }
                // New stages
                case "essentiality_prediction":
                    updates.essentiality = event.data;
                    break;
                case "kinetics_enrichment":
                    updates.kinetics = event.data;
                    updates.kineticsProgress = null;
                    break;
                case "cellspec_assembly":
                    updates.cellSpec = event.data;
                    break;
                case "simulation": {
                    const simData = event.data;
                    updates.simulationResult = {
                        summary: simData.summary ?? {},
                        time_series: simData.time_series ?? [],
                        total_divisions: simData.total_divisions ?? 0,
                        doubling_time: simData.doubling_time ?? null,
                    };
                    // Copy final time_series into store for charts
                    updates.simulationSnapshots = simData.time_series ?? [];
                    updates.simulationProgress = 1.0;
                    break;
                }
                case "validation":
                    updates.validation = event.data;
                    break;
                // Single gene deep analysis
                case "gene_analysis": {
                    const pred = event.data;
                    const pMap = new Map(state.predictions);
                    pMap.set(pred.locus_tag, pred);
                    updates.predictions = pMap;
                    updates.geneAnalysisStatus = "completed";
                    updates.geneAnalysisProgress = 1.0;
                    updates.geneAnalysisMessage = "";
                    // Update genome gene color/category in the circle
                    if (state.genome && pred.suggested_category !== "unknown") {
                        const CATEGORY_COLORS = {
                            gene_expression: "#22d3ee",
                            cell_membrane: "#a78bfa",
                            metabolism: "#34d399",
                            genome_preservation: "#60a5fa",
                            predicted: "#fb923c",
                        };
                        const updatedGenes = state.genome.genes.map((g) => {
                            if (g.locus_tag === pred.locus_tag) {
                                return {
                                    ...g,
                                    functional_category: pred.suggested_category,
                                    prediction_source: pred.prediction_source || "genelife",
                                    color: CATEGORY_COLORS[pred.suggested_category] || "#fb923c",
                                };
                            }
                            return g;
                        });
                        updates.genome = { ...state.genome, genes: updatedGenes };
                    }
                    break;
                }
            }
        }
        // Track running-state progress for various stages
        if (event.status === "running" && event.data) {
            const d = event.data;
            if (event.stage === "functional_prediction") {
                if (d.phase !== undefined) {
                    updates.pipelinePhase = {
                        phase: d.phase,
                        message: d.message || "",
                    };
                }
                if (d.analyzed !== undefined) {
                    updates.predictionProgress = {
                        analyzed: d.analyzed,
                        total: d.total,
                    };
                }
            }
            if (event.stage === "kinetics_enrichment" && d.done !== undefined) {
                updates.kineticsProgress = {
                    done: d.done,
                    total: d.total,
                    measured_pct: d.measured_pct,
                    assumed_pct: d.assumed_pct,
                };
            }
            if (event.stage === "simulation" && d.snapshot) {
                // Push to external buffer (not into state) during streaming
                simulationBuffer.push(d.snapshot);
                updates.simulationProgress = d.progress ?? state.simulationProgress;
                updates.simulationWallTime = d.wall_time ?? state.simulationWallTime;
            }
            if (event.stage === "gene_analysis") {
                updates.geneAnalysisStatus = "running";
                updates.geneAnalysisProgress = event.progress;
                updates.geneAnalysisMessage = d.message || "";
            }
        }
        if (event.stage === "pipeline" && (event.status === "completed" || event.status === "failed")) {
            updates.isAnalyzing = false;
        }
        if (event.stage === "gene_analysis" && event.status === "failed") {
            updates.geneAnalysisStatus = "failed";
            updates.geneAnalysisMessage = event.error || "Analysis failed";
        }
        return updates;
    }),
    selectGene: (gene) => set({ selectedGene: gene }),
    setResearchStatus: (tag, status) => set((state) => {
        const m = new Map(state.researchStatus);
        m.set(tag, status);
        return { researchStatus: m };
    }),
    reset: () => {
        simulationBuffer.clear();
        set({
            query: "",
            mode: null,
            isAnalyzing: false,
            stages: {},
            geneRecord: null,
            sequenceAnalysis: null,
            annotation: null,
            genome: null,
            selectedGene: null,
            predictionProgress: null,
            pipelinePhase: null,
            functionalAnalysis: null,
            predictions: new Map(),
            essentiality: null,
            kinetics: null,
            kineticsProgress: null,
            cellSpec: null,
            simulationSnapshots: [],
            simulationProgress: 0,
            simulationWallTime: 0,
            simulationResult: null,
            validation: null,
            researchStatus: new Map(),
        });
    },
}));
