import { useCallback, useEffect, useRef, useState } from "react";
import { useGeneStore } from "../store";
import { usePipeline } from "./usePipeline";
import { useGeneAnalysis } from "./useGeneAnalysis";
import type { GenomeGene } from "../types";

const API = `${location.protocol}//${location.host}/api/v1/genes`;

export interface ResearchQueueItem {
  locus_tag: string;
  gene_name: string | null;
  product: string | null;
  protein_sequence: string | null;
  priority: number;
}

export interface ResearchManagerState {
  // Kept from original
  hydrating: boolean;
  showSearch: boolean;
  toggleSearch: () => void;
  // Queue
  queue: ResearchQueueItem[];
  totalQueued: number;
  queueLoading: boolean;
  refetchQueue: () => Promise<void>;
  // Batch
  batchActive: boolean;
  batchCurrentGene: string | null;
  batchCompleted: number;
  batchTotal: number;
  batchProgress: number;
  startBatchResearch: () => void;
  stopBatchResearch: () => void;
  // Single gene
  researchSingleGene: (locusTag: string) => void;
}

export function useResearchManager(): ResearchManagerState {
  const { genome, isAnalyzing, handleEvent, geneAnalysisStatus } =
    useGeneStore();
  const { analyze: triggerPipeline } = usePipeline();
  const { analyzeGene } = useGeneAnalysis();

  const [hydrating, setHydrating] = useState(true);
  const [showSearch, setShowSearch] = useState(false);
  const [queue, setQueue] = useState<ResearchQueueItem[]>([]);
  const [queueLoading, setQueueLoading] = useState(false);

  // Batch state
  const [batchActive, setBatchActive] = useState(false);
  const [batchCurrentGene, setBatchCurrentGene] = useState<string | null>(null);
  const [batchCompleted, setBatchCompleted] = useState(0);
  const [batchTotal, setBatchTotal] = useState(0);

  const batchQueueRef = useRef<ResearchQueueItem[]>([]);
  const batchIndexRef = useRef(0);
  const loopActiveRef = useRef(false);
  const hasInitRef = useRef(false);

  const toggleSearch = useCallback(() => setShowSearch((s) => !s), []);

  // ── Phase 1: Hydrate or trigger pipeline on mount ──────────────
  useEffect(() => {
    if (hasInitRef.current) return;
    hasInitRef.current = true;

    (async () => {
      try {
        const res = await fetch(`${API}/genome/status`);
        if (!res.ok) {
          setHydrating(false);
          setShowSearch(true);
          return;
        }
        const status = await res.json();

        if (status.has_genome) {
          // Try genome-specific hydrate first, fall back to legacy endpoint
          const activeId = useGeneStore.getState().activeGenomeId;
          const hydrateUrl = activeId
            ? `${location.protocol}//${location.host}/api/v1/genomes/${activeId}/hydrate`
            : `${API}/genome/hydrate`;
          const hydRes = await fetch(hydrateUrl);
          if (hydRes.ok) {
            const genomeData = await hydRes.json();
            handleEvent({
              stage: "genome_ingest",
              status: "completed",
              data: genomeData,
              error: null,
              progress: 1.0,
            });
          }
          setHydrating(false);
        } else {
          setHydrating(false);
          triggerPipeline("JCVI-syn3.0");
        }
      } catch {
        setHydrating(false);
        setShowSearch(true);
      }
    })();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Phase 2: Fetch research queue once genome is loaded ────────
  const fetchQueue = useCallback(async () => {
    if (!genome) return;
    setQueueLoading(true);
    try {
      const res = await fetch(`${API}/research/queue?limit=50`);
      if (!res.ok) return;
      const items: ResearchQueueItem[] = await res.json();
      setQueue(items);
    } catch {
      // Silently skip if queue fetch fails
    } finally {
      setQueueLoading(false);
    }
  }, [genome]);

  useEffect(() => {
    if (!genome || isAnalyzing) return;
    fetchQueue();
  }, [genome, isAnalyzing, fetchQueue]);

  const refetchQueue = useCallback(async () => {
    await fetchQueue();
  }, [fetchQueue]);

  // ── Batch research functions ───────────────────────────────────

  const startBatchResearch = useCallback(() => {
    if (batchActive || queue.length === 0 || !genome) return;
    batchQueueRef.current = [...queue];
    batchIndexRef.current = 0;
    loopActiveRef.current = true;
    setBatchActive(true);
    setBatchCompleted(0);
    setBatchTotal(queue.length);
    setBatchCurrentGene(null);
  }, [batchActive, queue, genome]);

  const stopBatchResearch = useCallback(() => {
    setBatchActive(false);
    loopActiveRef.current = false;
    setBatchCurrentGene(null);
  }, []);

  // Batch sequential loop — drives analysis one gene at a time
  useEffect(() => {
    if (!batchActive || !loopActiveRef.current || !genome) return;

    // Don't start a new analysis while one is running
    if (geneAnalysisStatus === "running") return;

    const idx = batchIndexRef.current;
    const batchQueue = batchQueueRef.current;

    // Previous gene completed/failed — advance
    if (batchCurrentGene && (geneAnalysisStatus === "completed" || geneAnalysisStatus === "failed")) {
      const nextIdx = idx + 1;
      if (nextIdx >= batchQueue.length) {
        // All done
        setBatchActive(false);
        loopActiveRef.current = false;
        setBatchCurrentGene(null);
        setBatchCompleted(batchQueue.length);
        return;
      }
      batchIndexRef.current = nextIdx;
      setBatchCompleted(idx + 1);
      const timer = setTimeout(() => launchNext(nextIdx), 2000);
      return () => clearTimeout(timer);
    }

    // First launch
    if (!batchCurrentGene && batchQueue.length > 0) {
      launchNext(idx);
    }

    function launchNext(i: number) {
      const item = batchQueue[i];
      if (!item) return;

      const genomeGene = genome!.genes.find(
        (g: GenomeGene) => g.locus_tag === item.locus_tag
      );
      if (!genomeGene || !genomeGene.protein_sequence) {
        // Skip genes without protein sequence
        batchIndexRef.current = i + 1;
        setBatchCompleted((c) => c + 1);
        if (i + 1 >= batchQueue.length) {
          setBatchActive(false);
          loopActiveRef.current = false;
          setBatchCurrentGene(null);
        }
        return;
      }

      setBatchCurrentGene(item.locus_tag);
      analyzeGene(genomeGene);
    }
  }, [batchActive, genome, geneAnalysisStatus, batchCurrentGene, analyzeGene]);

  // ── Single gene research ───────────────────────────────────────

  const researchSingleGene = useCallback(
    (locusTag: string) => {
      if (batchActive || !genome) return;
      const genomeGene = genome.genes.find(
        (g: GenomeGene) => g.locus_tag === locusTag
      );
      if (!genomeGene || !genomeGene.protein_sequence) return;
      analyzeGene(genomeGene);
    },
    [batchActive, genome, analyzeGene]
  );

  const batchProgress = batchTotal > 0 ? batchCompleted / batchTotal : 0;

  return {
    hydrating,
    showSearch,
    toggleSearch,
    queue,
    totalQueued: queue.length,
    queueLoading,
    refetchQueue,
    batchActive,
    batchCurrentGene,
    batchCompleted,
    batchTotal,
    batchProgress,
    startBatchResearch,
    stopBatchResearch,
    researchSingleGene,
  };
}
