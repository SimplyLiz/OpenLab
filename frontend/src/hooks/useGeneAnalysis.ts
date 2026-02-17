import { useCallback, useRef } from "react";
import { useGeneStore } from "../store";
import type { GenomeGene, PipelineEvent } from "../types";

const WS_URL = `${location.protocol === "https:" ? "wss:" : "ws:"}//${location.host}/ws/analyze`;

export function useGeneAnalysis() {
  const wsRef = useRef<WebSocket | null>(null);
  const { handleEvent } = useGeneStore();

  const analyzeGene = useCallback(
    (gene: GenomeGene) => {
      // Close any previous gene analysis connection
      if (wsRef.current) {
        wsRef.current.close();
      }

      // Mark gene analysis as starting
      useGeneStore.getState().startGeneAnalysis(gene.locus_tag);

      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        ws.send(
          JSON.stringify({
            locus_tag: gene.locus_tag,
            protein_sequence: gene.protein_sequence,
            gene_name: gene.gene_name,
            product: gene.product,
          })
        );
      };

      ws.onmessage = (msg) => {
        try {
          const event: PipelineEvent = JSON.parse(msg.data);
          handleEvent(event);
        } catch {
          console.error("Failed to parse gene analysis event:", msg.data);
        }
      };

      ws.onerror = () => {
        handleEvent({
          stage: "gene_analysis",
          status: "failed",
          data: null,
          error: "WebSocket connection failed",
          progress: 0,
        });
      };

      ws.onclose = () => {
        wsRef.current = null;
      };
    },
    [handleEvent]
  );

  const cancel = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  return { analyzeGene, cancel };
}
