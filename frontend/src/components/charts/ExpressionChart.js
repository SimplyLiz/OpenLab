import { jsx as _jsx } from "react/jsx-runtime";
import { useRef, useEffect } from "react";
import { drawChart } from "../../utils/chartHelpers";
export function ExpressionChart({ snapshots }) {
    const canvasRef = useRef(null);
    useEffect(() => {
        if (!canvasRef.current || snapshots.length < 2)
            return;
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
    return _jsx("canvas", { ref: canvasRef, className: "sim-chart-canvas" });
}
