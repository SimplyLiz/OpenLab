import { useRef, useEffect } from "react";
import type { SimulationSnapshot } from "../../types";
import { drawChart } from "../../utils/chartHelpers";

export function ExpressionChart({ snapshots }: { snapshots: SimulationSnapshot[] }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    if (!canvasRef.current || snapshots.length < 2) return;

    drawChart(canvasRef.current, {
      title: "Gene Expression",
      xLabel: "Time",
      yLabel: "Total Protein (copies)",
      yLabelRight: "Total mRNA (copies)",
      lines: [
        {
          label: "Protein",
          color: "#22d3ee",
          points: snapshots.map((s) => ({ x: s.time, y: s.total_protein })),
        },
      ],
      linesRight: [
        {
          label: "mRNA",
          color: "#34d399",
          points: snapshots.map((s) => ({ x: s.time, y: s.total_mrna })),
        },
      ],
    });
  }, [snapshots]);

  return <canvas ref={canvasRef} className="sim-chart-canvas" />;
}
