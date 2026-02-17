import { useState, useCallback } from "react";
import { useGeneStore } from "../store";
import type { SimulationResult, SimulationSnapshot } from "../types";

const API = `${location.protocol}//${location.host}/api/v1`;

export function useKnockout() {
  const [isRunning, setIsRunning] = useState(false);

  const runKnockout = useCallback(async () => {
    const { knockoutSet, activeGenomeId, cellSpec, setKnockoutSimResult } =
      useGeneStore.getState();

    if (knockoutSet.size === 0 || !activeGenomeId) return;

    if (!cellSpec) {
      console.warn("No CellSpec available. Run the full pipeline first.");
      return;
    }

    setIsRunning(true);

    try {
      const res = await fetch(`${API}/simulation/knockout`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          genome_id: activeGenomeId,
          knockouts: Array.from(knockoutSet),
          cellspec: cellSpec,
        }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Simulation failed" }));
        console.error("Knockout simulation failed:", err.detail);
        return;
      }

      const data = await res.json();

      const result: SimulationResult = {
        summary: data.summary ?? {},
        time_series: (data.time_series ?? []) as SimulationSnapshot[],
        total_divisions: data.summary?.divisions ?? 0,
        doubling_time: data.summary?.doublingTimeHours ?? null,
      };

      setKnockoutSimResult(result);
    } catch (e) {
      console.error("Knockout simulation error:", e);
    } finally {
      setIsRunning(false);
    }
  }, []);

  return { runKnockout, isRunning };
}
