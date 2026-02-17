import { useCallback } from 'react';
import { useCellForgeStore } from '@/stores/cellforgeStore';
import type { Perturbation } from '@/types/cellforge';

const API_BASE = '/api/v1/cellforge/simulations';

/**
 * Hook for interacting with the backend CellForge API.
 * For local-only simulation (no backend), use useCellForgeStore directly.
 */
export function useCellForgeSimulation() {
  const store = useCellForgeStore();

  const createSimulation = useCallback(async (organismName: string) => {
    const res = await fetch(API_BASE, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ organism_name: organismName, config: {} }),
    });
    return res.json();
  }, []);

  const startSimulation = useCallback(async (id: string) => {
    const res = await fetch(`${API_BASE}/${id}/start`, { method: 'POST' });
    return res.json();
  }, []);

  const stopSimulation = useCallback(async (id: string) => {
    const res = await fetch(`${API_BASE}/${id}/stop`, { method: 'POST' });
    return res.json();
  }, []);

  const injectPerturbation = useCallback(async (id: string, perturbation: Perturbation) => {
    const res = await fetch(`${API_BASE}/${id}/perturbation`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        perturbation_type: perturbation.perturbationType,
        target: perturbation.target,
        value: perturbation.value,
      }),
    });
    return res.json();
  }, []);

  return {
    ...store,
    createSimulation,
    startSimulation,
    stopSimulation,
    injectPerturbation,
  };
}
