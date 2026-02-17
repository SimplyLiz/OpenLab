import { useCallback, useRef } from "react";
import { useGeneStore } from "../store";
import type { PipelineEvent } from "../types";

const WS_URL = `${location.protocol === "https:" ? "wss:" : "ws:"}//${location.host}/ws/analyze`;

export function usePipeline() {
  const wsRef = useRef<WebSocket | null>(null);
  const { startAnalysis, handleEvent } = useGeneStore();

  const analyze = useCallback(
    (query: string) => {
      // Close any existing connection
      if (wsRef.current) {
        wsRef.current.close();
      }

      startAnalysis();

      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        ws.send(JSON.stringify({ query }));
      };

      ws.onmessage = (msg) => {
        try {
          const event: PipelineEvent = JSON.parse(msg.data);
          handleEvent(event);
        } catch {
          console.error("Failed to parse pipeline event:", msg.data);
        }
      };

      ws.onerror = (err) => {
        console.error("WebSocket error:", err);
        handleEvent({
          stage: "pipeline",
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
    [startAnalysis, handleEvent]
  );

  const cancel = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  return { analyze, cancel };
}
