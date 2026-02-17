import { create } from "zustand";
import type {
  PipelineEvent,
  GeneRecord,
  GenomeRecord,
  GenomeGene,
  GenomeSummary,
  SequenceAnalysisResult,
  AnnotationResult,
  FunctionalPrediction,
  GenomeFunctionalAnalysis,
  StageStatus,
  EssentialityResult,
  KineticsResult,
  CellSpec,
  SimulationSnapshot,
  SimulationResult,
  ValidationResult,
  ResearchStatus,
} from "./types";
import { simulationBuffer } from "./utils/simulationBuffer";

interface StageState {
  status: StageStatus;
  data: unknown;
  error: string | null;
}

interface GeneStore {
  // Query
  query: string;
  setQuery: (q: string) => void;

  // Mode (kept for backward compat, URL is now primary)
  mode: "gene" | "genome" | null;

  // Multi-genome
  activeGenomeId: number | null;
  genomes: GenomeSummary[];
  setActiveGenomeId: (id: number | null) => void;
  setGenomes: (g: GenomeSummary[]) => void;

  // Knockout
  knockoutSet: Set<string>;
  knockoutSimResult: SimulationResult | null;
  setKnockoutSet: (s: Set<string>) => void;
  setKnockoutSimResult: (r: SimulationResult | null) => void;

  // PiP
  petriPiP: boolean;
  setPetriPiP: (v: boolean) => void;

  // Pipeline state
  isAnalyzing: boolean;
  stages: Record<string, StageState>;

  // Single gene results
  geneRecord: GeneRecord | null;
  sequenceAnalysis: SequenceAnalysisResult | null;
  annotation: AnnotationResult | null;

  // Genome results
  genome: GenomeRecord | null;
  selectedGene: GenomeGene | null;
  predictionProgress: { analyzed: number; total: number } | null;
  pipelinePhase: { phase: number; message: string } | null;
  functionalAnalysis: GenomeFunctionalAnalysis | null;
  predictions: Map<string, FunctionalPrediction>;

  // DNAView integration
  essentiality: EssentialityResult | null;
  kinetics: KineticsResult | null;
  kineticsProgress: { done: number; total: number; measured_pct: number; assumed_pct: number } | null;
  cellSpec: CellSpec | null;
  simulationSnapshots: SimulationSnapshot[];
  simulationProgress: number;
  simulationWallTime: number;
  simulationResult: SimulationResult | null;
  validation: ValidationResult | null;

  // Gene-level deep analysis
  geneAnalysisStatus: StageStatus | null;
  geneAnalysisProgress: number;
  geneAnalysisMessage: string;
  geneAnalysisTarget: string | null;

  // Research cycle (DB-backed)
  researchStatus: Map<string, ResearchStatus>;

  // Actions
  startAnalysis: () => void;
  startGeneAnalysis: (locus_tag: string) => void;
  handleEvent: (event: PipelineEvent) => void;
  selectGene: (gene: GenomeGene | null) => void;
  setResearchStatus: (tag: string, status: ResearchStatus) => void;
  reset: () => void;
}

export const useGeneStore = create<GeneStore>((set) => ({
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

  startGeneAnalysis: (locus_tag: string) =>
    set({
      geneAnalysisStatus: "running",
      geneAnalysisProgress: 0,
      geneAnalysisMessage: "Starting deep analysis...",
      geneAnalysisTarget: locus_tag,
    }),

  handleEvent: (event) =>
    set((state) => {
      const newStages = { ...state.stages };
      newStages[event.stage] = {
        status: event.status,
        data: event.data,
        error: event.error,
      };

      const updates: Partial<GeneStore> = { stages: newStages };

      if (event.status === "completed" && event.data) {
        switch (event.stage) {
          // Single gene mode
          case "ingest":
            updates.mode = "gene";
            updates.geneRecord = event.data as unknown as GeneRecord;
            break;
          case "sequence_analysis":
            updates.sequenceAnalysis = event.data as unknown as SequenceAnalysisResult;
            break;
          case "annotation":
            updates.annotation = event.data as unknown as AnnotationResult;
            break;

          // Genome mode
          case "genome_ingest":
            updates.mode = "genome";
            updates.genome = event.data as unknown as GenomeRecord;
            break;
          case "genome_updated":
            updates.genome = event.data as unknown as GenomeRecord;
            break;
          case "functional_prediction": {
            const analysis = event.data as unknown as GenomeFunctionalAnalysis;
            updates.functionalAnalysis = analysis;
            if (analysis?.predictions) {
              const pMap = new Map<string, FunctionalPrediction>();
              for (const pred of analysis.predictions) {
                pMap.set(pred.locus_tag, pred);
              }
              updates.predictions = pMap;
            }
            break;
          }

          // New stages
          case "essentiality_prediction":
            updates.essentiality = event.data as unknown as EssentialityResult;
            break;
          case "kinetics_enrichment":
            updates.kinetics = event.data as unknown as KineticsResult;
            updates.kineticsProgress = null;
            break;
          case "cellspec_assembly":
            updates.cellSpec = event.data as unknown as CellSpec;
            break;
          case "simulation": {
            const simData = event.data as Record<string, unknown>;
            updates.simulationResult = {
              summary: (simData.summary as Record<string, unknown>) ?? {},
              time_series: (simData.time_series as SimulationSnapshot[]) ?? [],
              total_divisions: (simData.total_divisions as number) ?? 0,
              doubling_time: (simData.doubling_time as number | null) ?? null,
            };
            // Copy final time_series into store for charts
            updates.simulationSnapshots = (simData.time_series as SimulationSnapshot[]) ?? [];
            updates.simulationProgress = 1.0;
            break;
          }
          case "validation":
            updates.validation = event.data as unknown as ValidationResult;
            break;

          // Single gene deep analysis
          case "gene_analysis": {
            const pred = event.data as unknown as FunctionalPrediction;
            const pMap = new Map(state.predictions);
            pMap.set(pred.locus_tag, pred);
            updates.predictions = pMap;
            updates.geneAnalysisStatus = "completed";
            updates.geneAnalysisProgress = 1.0;
            updates.geneAnalysisMessage = "";

            // Update genome gene color/category in the circle
            if (state.genome && pred.suggested_category !== "unknown") {
              const CATEGORY_COLORS: Record<string, string> = {
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
                    prediction_source: pred.prediction_source || ("genelife" as const),
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
        const d = event.data as Record<string, unknown>;

        if (event.stage === "functional_prediction") {
          if (d.phase !== undefined) {
            updates.pipelinePhase = {
              phase: d.phase as number,
              message: (d.message as string) || "",
            };
          }
          if (d.analyzed !== undefined) {
            updates.predictionProgress = {
              analyzed: d.analyzed as number,
              total: d.total as number,
            };
          }
        }

        if (event.stage === "kinetics_enrichment" && d.done !== undefined) {
          updates.kineticsProgress = {
            done: d.done as number,
            total: d.total as number,
            measured_pct: d.measured_pct as number,
            assumed_pct: d.assumed_pct as number,
          };
        }

        if (event.stage === "simulation" && d.snapshot) {
          // Push to external buffer (not into state) during streaming
          simulationBuffer.push(d.snapshot as SimulationSnapshot);
          updates.simulationProgress = (d.progress as number) ?? state.simulationProgress;
          updates.simulationWallTime = (d.wall_time as number) ?? state.simulationWallTime;
        }

        if (event.stage === "gene_analysis") {
          updates.geneAnalysisStatus = "running";
          updates.geneAnalysisProgress = event.progress;
          updates.geneAnalysisMessage = (d.message as string) || "";
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

  setResearchStatus: (tag, status) =>
    set((state) => {
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
