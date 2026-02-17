import { useGeneStore } from "../store";
import { GrowthChart } from "./charts/GrowthChart";
import { MetaboliteChart } from "./charts/MetaboliteChart";
import { ExpressionChart } from "./charts/ExpressionChart";
import { GrowthRateChart } from "./charts/GrowthRateChart";

export function SimulationDashboard() {
  const { simulationSnapshots, simulationResult, simulationProgress, simulationWallTime } = useGeneStore();

  // Don't render until we have simulation data
  if (simulationSnapshots.length < 2 && simulationProgress === 0) return null;

  const summary = simulationResult?.summary;
  const doublingTime = summary?.doubling_time_hours as number | undefined;
  const totalDivisions = simulationResult?.total_divisions ?? 0;

  return (
    <div className="panel sim-dashboard">
      <h2 className="panel-title">Whole-Cell Simulation</h2>
      <p className="panel-sub">
        {simulationProgress < 1
          ? `Simulating... ${(simulationProgress * 100).toFixed(0)}% (${simulationWallTime.toFixed(1)}s)`
          : `Complete — ${totalDivisions} divisions`}
        {doublingTime != null && ` — doubling time: ${doublingTime.toFixed(1)}h`}
      </p>

      {/* Summary stats */}
      {summary && (
        <div className="stats-grid sim-stats">
          <div className="stat-card">
            <div className="stat-value" style={{ color: "#22d3ee" }}>
              {totalDivisions}
            </div>
            <div className="stat-label">divisions</div>
          </div>
          {doublingTime != null && (
            <div className="stat-card">
              <div className="stat-value" style={{ color: "#34d399" }}>
                {doublingTime.toFixed(1)}h
              </div>
              <div className="stat-label">doubling time</div>
            </div>
          )}
          <div className="stat-card">
            <div className="stat-value" style={{ color: "#fb923c" }}>
              {((summary.wall_time_seconds as number) ?? simulationWallTime).toFixed(1)}s
            </div>
            <div className="stat-label">wall time</div>
          </div>
          <div className="stat-card">
            <div className="stat-value" style={{ color: "#a78bfa" }}>
              {simulationSnapshots.length}
            </div>
            <div className="stat-label">snapshots</div>
          </div>
        </div>
      )}

      {/* Charts grid */}
      <div className="sim-charts-grid">
        <div className="sim-chart-panel">
          <GrowthChart snapshots={simulationSnapshots} />
        </div>
        <div className="sim-chart-panel">
          <MetaboliteChart snapshots={simulationSnapshots} />
        </div>
        <div className="sim-chart-panel">
          <ExpressionChart snapshots={simulationSnapshots} />
        </div>
        <div className="sim-chart-panel">
          <GrowthRateChart snapshots={simulationSnapshots} />
        </div>
      </div>
    </div>
  );
}
