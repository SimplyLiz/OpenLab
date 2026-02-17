import { jsx as _jsx } from "react/jsx-runtime";
import { useRef, useEffect } from "react";
import { drawChart } from "../../utils/chartHelpers";
export function GrowthChart({ snapshots }) {
    const canvasRef = useRef(null);
    useEffect(() => {
        if (!canvasRef.current || snapshots.length < 2)
            return;
        // Find division times
        const divTimes = [];
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
    return _jsx("canvas", { ref: canvasRef, className: "sim-chart-canvas" });
}
