import { useEffect, useRef } from 'react';
import { useCellForgeStore } from '@/stores/cellforgeStore';
import type { SimulationState } from '@/types/cellforge';

/**
 * Hook for WebSocket streaming from backend CellForge API.
 * Connects to the backend and updates the store with real-time state.
 * For local-only simulation, this is not needed.
 */
export function useCellForgeStreaming(simulationId: string | null) {
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!simulationId) return;

    const ws = new WebSocket(`ws://localhost:8000/ws/cellforge/simulations/${simulationId}`);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('[CellForge WS] Connected:', simulationId);
    };

    ws.onclose = () => {
      console.log('[CellForge WS] Disconnected');
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'state_update' && data.state) {
          const state: SimulationState = {
            simulationId: data.simulation_id,
            time: data.time,
            metaboliteConcentrations: data.state.metabolite_concentrations ?? {},
            mrnaCounts: data.state.mrna_counts ?? {},
            proteinCounts: data.state.protein_counts ?? {},
            fluxDistribution: data.state.flux_distribution ?? {},
            growthRate: data.state.growth_rate ?? 0,
            cellMass: data.state.cell_mass ?? 0,
            replicationProgress: data.state.replication_progress ?? 0,
          };
          useCellForgeStore.getState().setState(state);
        }
      } catch {
        // ignore parse errors
      }
    };

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [simulationId]);

  return { ws: wsRef.current };
}
