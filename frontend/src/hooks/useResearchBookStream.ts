import { useEffect, useRef, useCallback } from "react";
import { useResearchBookStore } from "../stores/researchBookStore";

/**
 * WebSocket hook for real-time thread updates.
 * Connects to /ws/researchbook/{threadId} and dispatches events to store.
 */
export function useResearchBookStream(threadId: number | null) {
  const wsRef = useRef<WebSocket | null>(null);
  const fetchThread = useResearchBookStore((s) => s.fetchThread);

  const connect = useCallback(() => {
    if (!threadId) return;

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const url = `${protocol}//${window.location.host}/ws/researchbook/${threadId}`;

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        // On any update, refresh the thread
        if (data.type === "comment" || data.type === "challenge" || data.type === "fork") {
          fetchThread(threadId);
        }
      } catch {
        // ignore parse errors
      }
    };

    ws.onclose = () => {
      // Auto-reconnect after 3s
      setTimeout(() => {
        if (threadId) connect();
      }, 3000);
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [threadId, fetchThread]);

  useEffect(() => {
    connect();
    return () => {
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [connect]);

  return wsRef;
}
