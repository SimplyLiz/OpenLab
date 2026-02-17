import { jsx as _jsx } from "react/jsx-runtime";
import { useRef, useEffect } from "react";
import { drawChart } from "../../utils/chartHelpers";
export function GrowthRateChart({ snapshots }) {
    const canvasRef = useRef(null);
    useEffect(() => {
        if (!canvasRef.current || snapshots.length < 2)
            return;
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
    return _jsx("canvas", { ref: canvasRef, className: "sim-chart-canvas" });
}
