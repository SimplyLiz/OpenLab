import { useRef, useEffect } from "react";
import type { SimulationSnapshot } from "../../types";
import { drawChart } from "../../utils/chartHelpers";

export function GrowthRateChart({ snapshots }: { snapshots: SimulationSnapshot[] }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    if (!canvasRef.current || snapshots.length < 2) return;

    drawChart(canvasRef.current, {
      title: "Growth Rate",
      xLabel: "Time",
      yLabel: "Growth Rate (1/s)",
      lines: [
        {
          label: "Growth Rate",
          color: "#fb923c",
          points: snapshots.map((s) => ({ x: s.time, y: s.growth_rate })),
          width: 1.5,
        },
      ],
    });
  }, [snapshots]);

  return <canvas ref={canvasRef} className="sim-chart-canvas" />;
}
