import { useRef, useEffect } from "react";
import type { SimulationSnapshot } from "../../types";
import { drawChart } from "../../utils/chartHelpers";

export function MetaboliteChart({ snapshots }: { snapshots: SimulationSnapshot[] }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    if (!canvasRef.current || snapshots.length < 2) return;

    drawChart(canvasRef.current, {
      title: "Metabolites",
      xLabel: "Time",
      yLabel: "Concentration (mM)",
      lines: [
        {
          label: "ATP",
          color: "#f87171",
          points: snapshots.map((s) => ({ x: s.time, y: s.atp })),
        },
        {
          label: "GTP",
          color: "#60a5fa",
          points: snapshots.map((s) => ({ x: s.time, y: s.gtp })),
        },
        {
          label: "Glucose",
          color: "#fbbf24",
          points: snapshots.map((s) => ({ x: s.time, y: s.glucose })),
        },
        {
          label: "AA Pool",
          color: "#a78bfa",
          points: snapshots.map((s) => ({ x: s.time, y: s.aa_pool })),
        },
      ],
    });
  }, [snapshots]);

  return <canvas ref={canvasRef} className="sim-chart-canvas" />;
}
