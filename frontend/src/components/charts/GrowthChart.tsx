import { useRef, useEffect } from "react";
import type { SimulationSnapshot } from "../../types";
import { drawChart } from "../../utils/chartHelpers";

export function GrowthChart({ snapshots }: { snapshots: SimulationSnapshot[] }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    if (!canvasRef.current || snapshots.length < 2) return;

    // Find division times
    const divTimes: number[] = [];
    for (let i = 1; i < snapshots.length; i++) {
      if (snapshots[i].division_count > snapshots[i - 1].division_count) {
        divTimes.push(snapshots[i].time);
      }
    }

    drawChart(canvasRef.current, {
      title: "Growth",
      xLabel: "Time",
      yLabel: "Volume (fL) / Mass (fg)",
      lines: [
        {
          label: "Volume",
          color: "#22d3ee",
          points: snapshots.map((s) => ({ x: s.time, y: s.volume })),
        },
        {
          label: "Dry Mass",
          color: "#34d399",
          points: snapshots.map((s) => ({ x: s.time, y: s.dry_mass })),
        },
      ],
      divisionTimes: divTimes,
    });
  }, [snapshots]);

  return <canvas ref={canvasRef} className="sim-chart-canvas" />;
}
