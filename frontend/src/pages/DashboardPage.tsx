import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useGeneStore } from "../store";
import { useGenomeLoader } from "../hooks/useGenomes";
import { CellSimulation } from "../components/CellSimulation";
import type { ResearchSummary } from "../types";

const API = `${location.protocol}//${location.host}/api/v1`;

export function DashboardPage() {
  const { genomeId } = useParams();
  const navigate = useNavigate();
  useGenomeLoader(genomeId);

  const genome = useGeneStore((s) => s.genome);
  const simulationResult = useGeneStore((s) => s.simulationResult);
  const [summary, setSummary] = useState<ResearchSummary | null>(null);

  useEffect(() => {
    fetch(`${API}/genes/research/summary`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => { if (d) setSummary(d); })
      .catch(() => {});
  }, [genome]);

  if (!genome) {
    return <div className="page-loading">Loading dashboard...</div>;
  }

  const researchPct = summary
    ? Math.round(((summary.total_with_evidence) / Math.max(summary.total_stored, 1)) * 100)
    : 0;

  return (
    <div className="page dashboard-page">
      <div className="dashboard-header">
        <h1 className="dashboard-title">{genome.organism}</h1>
        <p className="dashboard-sub">{genome.accession} — {genome.description}</p>
      </div>

      {/* KPI Row */}
      <div className="stats-grid dashboard-kpi">
        <div className="stat-card">
          <div className="stat-value" style={{ color: "#22d3ee" }}>{genome.total_genes}</div>
          <div className="stat-label">Total Genes</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ color: "#34d399" }}>{researchPct}%</div>
          <div className="stat-label">Researched</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ color: "#a78bfa" }}>
            {simulationResult ? "Complete" : "Idle"}
          </div>
          <div className="stat-label">Simulation</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ color: "#f87171" }}>{genome.genes_unknown}</div>
          <div className="stat-label">Unknown</div>
        </div>
      </div>

      {/* Main dashboard grid */}
      <div className="dashboard-grid">
        {/* Category breakdown */}
        <div className="panel dashboard-categories">
          <h2 className="panel-title">Gene Categories</h2>
          <CategoryBreakdown genome={genome} />
        </div>

        {/* Mini Petri Dish */}
        <div
          className="panel dashboard-mini-petri"
          onClick={() => navigate(`/g/${genomeId}/petri`)}
          style={{ cursor: "pointer" }}
        >
          <h2 className="panel-title">Virtual Cell</h2>
          <CellSimulation compact />
        </div>
      </div>

      {/* Research Progress */}
      {summary && (
        <div className="panel dashboard-research">
          <h2 className="panel-title">Research Progress</h2>
          <div className="dashboard-progress-grid">
            <ProgressRing
              label="Stored"
              value={summary.total_stored}
              total={genome.total_genes}
              color="#94a3b8"
            />
            <ProgressRing
              label="Evidence"
              value={summary.total_with_evidence}
              total={genome.total_genes}
              color="#22d3ee"
            />
            <ProgressRing
              label="Hypotheses"
              value={summary.total_with_hypothesis}
              total={genome.total_genes}
              color="#fb923c"
            />
            <ProgressRing
              label="Graduated"
              value={summary.total_graduated}
              total={genome.total_genes}
              color="#34d399"
            />
          </div>
        </div>
      )}

      {/* Activity Feed */}
      {summary && summary.needs_review.length > 0 && (
        <div className="panel dashboard-activity">
          <h2 className="panel-title">Needs Review</h2>
          <div className="dashboard-feed">
            {summary.needs_review.slice(0, 10).map((item) => (
              <div key={item.locus_tag} className="dashboard-feed-item">
                <span className="dashboard-feed-tag">{item.locus_tag}</span>
                <span className="dashboard-feed-title">{item.hypothesis_title}</span>
                <span className="dashboard-feed-conf">
                  {item.confidence != null ? `${(item.confidence * 100).toFixed(0)}%` : "—"}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function CategoryBreakdown({ genome }: { genome: { genes: { functional_category: string }[] } }) {
  const counts: Record<string, number> = {};
  for (const g of genome.genes) {
    counts[g.functional_category] = (counts[g.functional_category] || 0) + 1;
  }

  const COLORS: Record<string, string> = {
    gene_expression: "#22d3ee",
    cell_membrane: "#a78bfa",
    metabolism: "#34d399",
    genome_preservation: "#60a5fa",
    predicted: "#fb923c",
    unknown: "#f87171",
  };
  const LABELS: Record<string, string> = {
    gene_expression: "Gene Expression",
    cell_membrane: "Cell Membrane",
    metabolism: "Metabolism",
    genome_preservation: "Genome Preservation",
    predicted: "Predicted",
    unknown: "Unknown",
  };

  const total = genome.genes.length;

  return (
    <div className="category-breakdown">
      {Object.entries(counts)
        .sort((a, b) => b[1] - a[1])
        .map(([cat, count]) => (
          <div key={cat} className="category-row">
            <span className="category-dot" style={{ background: COLORS[cat] || "#888" }} />
            <span className="category-label">{LABELS[cat] || cat}</span>
            <span className="category-bar-wrap">
              <span
                className="category-bar"
                style={{
                  width: `${(count / total) * 100}%`,
                  background: COLORS[cat] || "#888",
                }}
              />
            </span>
            <span className="category-count">{count}</span>
          </div>
        ))}
    </div>
  );
}

function ProgressRing({
  label,
  value,
  total,
  color,
}: {
  label: string;
  value: number;
  total: number;
  color: string;
}) {
  const pct = total > 0 ? value / total : 0;
  const r = 36;
  const circ = 2 * Math.PI * r;
  const offset = circ * (1 - pct);

  return (
    <div className="progress-ring-item">
      <svg width="88" height="88" viewBox="0 0 88 88">
        <circle cx="44" cy="44" r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="6" />
        <circle
          cx="44"
          cy="44"
          r={r}
          fill="none"
          stroke={color}
          strokeWidth="6"
          strokeDasharray={circ}
          strokeDashoffset={offset}
          strokeLinecap="round"
          transform="rotate(-90 44 44)"
          style={{ transition: "stroke-dashoffset 0.5s ease" }}
        />
        <text x="44" y="40" textAnchor="middle" fill="white" fontSize="14" fontWeight="600">
          {value}
        </text>
        <text x="44" y="54" textAnchor="middle" fill="#94a3b8" fontSize="9">
          / {total}
        </text>
      </svg>
      <div className="progress-ring-label">{label}</div>
    </div>
  );
}
