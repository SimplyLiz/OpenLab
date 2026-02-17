import { useState } from "react";
import { useGeneStore } from "../../store";

type MetricTab = "growth" | "metabolites" | "expression" | "rate";

export function MetricsOverlay() {
  const [tab, setTab] = useState<MetricTab>("growth");
  const simulationSnapshots = useGeneStore((s) => s.simulationSnapshots);
  const knockoutSimResult = useGeneStore((s) => s.knockoutSimResult);

  const hasData = simulationSnapshots.length > 1;
  const koSeries = knockoutSimResult?.time_series ?? [];

  if (!hasData && koSeries.length === 0) {
    return (
      <div className="glass-panel metrics-overlay">
        <h3 className="glass-panel-title">Metrics</h3>
        <p className="metrics-empty">Run a simulation to see metrics</p>
      </div>
    );
  }

  const tabs: { key: MetricTab; label: string }[] = [
    { key: "growth", label: "Growth" },
    { key: "metabolites", label: "Meta" },
    { key: "expression", label: "Expr" },
    { key: "rate", label: "Rate" },
  ];

  return (
    <div className="glass-panel metrics-overlay">
      <h3 className="glass-panel-title">Metrics</h3>

      <div className="metrics-tabs">
        {tabs.map((t) => (
          <button
            key={t.key}
            className={`metrics-tab ${tab === t.key ? "metrics-tab-active" : ""}`}
            onClick={() => setTab(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="metrics-chart-area">
        <MiniChart tab={tab} snapshots={simulationSnapshots} koSnapshots={koSeries as unknown as Record<string, number>[]} />
      </div>
    </div>
  );
}

function MiniChart({
  tab,
  snapshots,
  koSnapshots,
}: {
  tab: MetricTab;
  snapshots: { time: number; volume: number; dry_mass: number; growth_rate: number; atp: number; glucose: number; total_protein: number; total_mrna: number }[];
  koSnapshots: Record<string, number>[];
}) {
  // Select data field based on tab
  const fieldMap: Record<MetricTab, { field: string; label: string; color: string }> = {
    growth: { field: "volume", label: "Volume (fL)", color: "#22d3ee" },
    metabolites: { field: "atp", label: "ATP (mM)", color: "#fdd835" },
    expression: { field: "total_protein", label: "Total Protein", color: "#4fc3f7" },
    rate: { field: "growth_rate", label: "Growth Rate", color: "#34d399" },
  };

  const { field, label, color } = fieldMap[tab];

  // Extract values
  const values = snapshots.map((s) => (s as Record<string, number>)[field]);

  if (values.length < 2) return null;

  const minV = Math.min(...values);
  const maxV = Math.max(...values);
  const range = maxV - minV || 1;
  const w = 260;
  const h = 120;

  // Build SVG path
  const points = values.map((v, i) => {
    const x = (i / (values.length - 1)) * w;
    const y = h - ((v - minV) / range) * (h - 10) - 5;
    return `${x},${y}`;
  });
  const path = `M${points.join(" L")}`;

  // KO overlay if available
  let koPath = "";
  if (koSnapshots.length > 1) {
    const koValues = koSnapshots.map((s) => s[field]);
    if (koValues.length > 1 && koValues[0] != null) {
      const koPoints = koValues.map((v, i) => {
        const x = (i / (koValues.length - 1)) * w;
        const y = h - ((v - minV) / range) * (h - 10) - 5;
        return `${x},${y}`;
      });
      koPath = `M${koPoints.join(" L")}`;
    }
  }

  return (
    <div className="mini-chart">
      <div className="mini-chart-label">{label}</div>
      <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`}>
        <path d={path} fill="none" stroke={color} strokeWidth="1.5" opacity="0.9" />
        {koPath && (
          <path d={koPath} fill="none" stroke="#f87171" strokeWidth="1.5" opacity="0.7" strokeDasharray="4 2" />
        )}
      </svg>
      {koPath && (
        <div className="mini-chart-legend">
          <span style={{ color }}>WT</span>
          <span style={{ color: "#f87171" }}>KO</span>
        </div>
      )}
    </div>
  );
}
