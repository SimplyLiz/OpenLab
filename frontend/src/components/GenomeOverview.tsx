import { useGeneStore } from "../store";
import type { GenomeGene, PredictionSource } from "../types";

const SOURCE_BADGE: Record<string, { label: string; color: string; bg: string }> = {
  genbank:  { label: "GenBank",    color: "#34d399", bg: "rgba(52,211,153,0.12)" },
  dnasyn:   { label: "DNASyn",     color: "#fb923c", bg: "rgba(251,146,60,0.12)" },
  curated:  { label: "Literature", color: "#2dd4bf", bg: "rgba(45,212,191,0.12)" },
  genelife: { label: "GeneLife",   color: "#818cf8", bg: "rgba(129,140,248,0.12)" },
};

function SourceBadge({ source }: { source: PredictionSource }) {
  const badge = SOURCE_BADGE[source];
  if (!badge) return null;
  return (
    <span
      className="source-badge"
      style={{ color: badge.color, backgroundColor: badge.bg }}
    >
      {badge.label}
    </span>
  );
}

export function GenomeOverview() {
  const { genome, pipelinePhase, isAnalyzing, functionalAnalysis, predictions, selectGene, essentiality, cellSpec, validation } = useGeneStore();
  if (!genome) return null;

  // Count genes by category
  const categories: Record<string, { count: number; color: string }> = {};
  for (const gene of genome.genes) {
    const cat = gene.functional_category;
    if (!categories[cat]) {
      categories[cat] = { count: 0, color: gene.color };
    }
    categories[cat].count++;
  }

  const catLabels: Record<string, string> = {
    gene_expression: "Gene Expression",
    cell_membrane: "Cell Membrane",
    metabolism: "Metabolism",
    genome_preservation: "Genome Preservation",
    predicted: "Predicted",
    unknown: "Unknown",
  };

  const mysteryGenes = genome.genes.filter((g) => g.functional_category === "unknown");
  const predictedGenes = genome.genes.filter((g) => g.functional_category === "predicted");

  // Break predicted genes by source
  const curatedGenes = predictedGenes.filter((g) => g.prediction_source === "curated");
  const dnasynGenes = predictedGenes.filter((g) => g.prediction_source === "dnasyn");
  const genelifeGenes = predictedGenes.filter((g) => g.prediction_source === "genelife");

  return (
    <div className="panel genome-overview">
      <h2 className="panel-title">{genome.organism}</h2>
      <p className="summary">{genome.description}</p>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-value">{genome.genome_length.toLocaleString()}</div>
          <div className="stat-label">base pairs</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{genome.total_genes}</div>
          <div className="stat-label">genes</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{genome.gc_content}%</div>
          <div className="stat-label">GC content</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ color: "#34d399" }}>{genome.genes_known}</div>
          <div className="stat-label">original annotation</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ color: "#f87171" }}>{mysteryGenes.length}</div>
          <div className="stat-label">still unknown</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{genome.is_circular ? "Circular" : "Linear"}</div>
          <div className="stat-label">topology</div>
        </div>
      </div>

      {/* Our findings breakdown */}
      {predictedGenes.length > 0 && (
        <div className="subsection findings-breakdown">
          <h3>Our Findings</h3>
          <div className="findings-row">
            {curatedGenes.length > 0 && (
              <div className="finding-stat">
                <span className="finding-count" style={{ color: "#2dd4bf" }}>{curatedGenes.length}</span>
                <SourceBadge source="curated" />
                <span className="finding-desc">from published research</span>
              </div>
            )}
            {dnasynGenes.length > 0 && (
              <div className="finding-stat">
                <span className="finding-count" style={{ color: "#fb923c" }}>{dnasynGenes.length}</span>
                <SourceBadge source="dnasyn" />
                <span className="finding-desc">evidence pipeline</span>
              </div>
            )}
            {genelifeGenes.length > 0 && (
              <div className="finding-stat">
                <span className="finding-count" style={{ color: "#818cf8" }}>{genelifeGenes.length}</span>
                <SourceBadge source="genelife" />
                <span className="finding-desc">live analysis</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Category breakdown bar */}
      <div className="subsection">
        <h3>Functional Categories</h3>
        <div className="category-bar">
          {Object.entries(categories)
            .sort((a, b) => b[1].count - a[1].count)
            .map(([cat, { count, color }]) => (
              <div
                key={cat}
                className="cat-segment"
                style={{ flex: count, backgroundColor: color }}
                title={`${catLabels[cat] ?? cat}: ${count} genes`}
              />
            ))}
        </div>
        <div className="category-legend">
          {Object.entries(categories)
            .sort((a, b) => b[1].count - a[1].count)
            .map(([cat, { count, color }]) => (
              <span key={cat} className="cat-legend-item">
                <span className="cat-dot" style={{ backgroundColor: color }} />
                {catLabels[cat] ?? cat}: {count}
              </span>
            ))}
        </div>
      </div>

      {/* Pipeline phase progress */}
      {isAnalyzing && pipelinePhase && (
        <div className="subsection pipeline-phase">
          <h3>Evidence Pipeline</h3>
          <div className="phase-indicators">
            {[1, 2, 3, 4, 5].map((p) => (
              <div
                key={p}
                className={`phase-dot ${p < pipelinePhase.phase ? "phase-done" : ""} ${p === pipelinePhase.phase ? "phase-active" : ""}`}
              >
                {p}
              </div>
            ))}
          </div>
          <p className="phase-message">{pipelinePhase.message}</p>
        </div>
      )}

      {/* Convergence summary */}
      {functionalAnalysis && functionalAnalysis.mean_convergence > 0 && (
        <div className="subsection convergence-summary">
          <h3>Evidence Convergence</h3>
          <div className="stats-grid" style={{ gridTemplateColumns: "1fr 1fr 1fr" }}>
            <div className="stat-card">
              <div className="stat-value" style={{ color: "#22d3ee" }}>
                {(functionalAnalysis.mean_convergence * 100).toFixed(1)}%
              </div>
              <div className="stat-label">mean convergence</div>
            </div>
            <div className="stat-card">
              <div className="stat-value" style={{ color: "#a78bfa" }}>
                {functionalAnalysis.total_analyzed}
              </div>
              <div className="stat-label">genes analyzed</div>
            </div>
            <div className="stat-card">
              <div className="stat-value" style={{ color: "#34d399" }}>
                {functionalAnalysis.genes_with_hypothesis}
              </div>
              <div className="stat-label">AI hypotheses</div>
            </div>
          </div>
        </div>
      )}

      {/* Mystery genes — still truly unknown */}
      <div className="subsection">
        <h3>Still Unknown ({mysteryGenes.length})</h3>
        {mysteryGenes.length === 0 ? (
          <p style={{ color: "#34d399", fontStyle: "italic" }}>
            All mystery genes have been assigned predicted functions.
          </p>
        ) : (
          <div className="gene-table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Locus Tag</th>
                  <th>Size</th>
                  <th>Convergence</th>
                  <th>Prediction</th>
                </tr>
              </thead>
              <tbody>
                {mysteryGenes
                  .sort((a, b) => {
                    const predA = predictions.get(a.locus_tag);
                    const predB = predictions.get(b.locus_tag);
                    return (predB?.convergence?.score ?? 0) - (predA?.convergence?.score ?? 0);
                  })
                  .slice(0, 50)
                  .map((g) => {
                    const pred = predictions.get(g.locus_tag);
                    const conv = pred?.convergence?.score ?? 0;
                    const hasHyp = !!pred?.hypothesis;
                    return (
                      <tr
                        key={g.locus_tag}
                        className="clickable-row"
                        onClick={() => selectGene(g)}
                      >
                        <td style={{ color: "#f87171" }}>{g.locus_tag}</td>
                        <td>{g.protein_length}aa</td>
                        <td>
                          {conv > 0 ? (
                            <span className="conv-badge" style={{
                              color: conv >= 0.5 ? "#34d399" : conv >= 0.2 ? "#fbbf24" : "#fb923c",
                            }}>
                              {(conv * 100).toFixed(0)}%
                            </span>
                          ) : (
                            <span style={{ color: "#475569" }}>—</span>
                          )}
                        </td>
                        <td>
                          {hasHyp ? (
                            <span className="hyp-badge">AI</span>
                          ) : pred?.predicted_function ? (
                            <span className="pred-text">{pred.predicted_function.slice(0, 40)}</span>
                          ) : (
                            <span style={{ color: "#475569" }}>{g.product || "unknown"}</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Predicted genes — grouped by source */}
      {curatedGenes.length > 0 && (
        <PredictedTable
          title="Literature-Curated"
          genes={curatedGenes}
          source="curated"
          predictions={predictions}
          selectGene={selectGene}
        />
      )}
      {dnasynGenes.length > 0 && (
        <PredictedTable
          title="DNASyn Pipeline"
          genes={dnasynGenes}
          source="dnasyn"
          predictions={predictions}
          selectGene={selectGene}
        />
      )}
      {genelifeGenes.length > 0 && (
        <PredictedTable
          title="GeneLife Analysis"
          genes={genelifeGenes}
          source="genelife"
          predictions={predictions}
          selectGene={selectGene}
        />
      )}

      {/* Essentiality summary */}
      {essentiality && (
        <div className="subsection">
          <h3>Essentiality Prediction</h3>
          <div className="stats-grid" style={{ gridTemplateColumns: "1fr 1fr" }}>
            <div className="stat-card">
              <div className="stat-value" style={{ color: "#f87171" }}>
                {essentiality.total_essential}
              </div>
              <div className="stat-label">essential genes</div>
            </div>
            <div className="stat-card">
              <div className="stat-value" style={{ color: "#34d399" }}>
                {essentiality.total_nonessential}
              </div>
              <div className="stat-label">non-essential genes</div>
            </div>
          </div>
        </div>
      )}

      {/* CellSpec summary */}
      {cellSpec && (
        <div className="subsection cellspec-summary">
          <h3>CellSpec Assembly</h3>
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-value" style={{ color: "#22d3ee" }}>
                {cellSpec.genes?.length ?? 0}
              </div>
              <div className="stat-label">genes</div>
            </div>
            <div className="stat-card">
              <div className="stat-value" style={{ color: "#a78bfa" }}>
                {cellSpec.reactions?.length ?? 0}
              </div>
              <div className="stat-label">reactions</div>
            </div>
            <div className="stat-card">
              <div className="stat-value" style={{ color: "#34d399" }}>
                {cellSpec.metabolites?.length ?? 0}
              </div>
              <div className="stat-label">metabolites</div>
            </div>
          </div>
          {cellSpec.provenance_summary && (
            <p className="cellspec-provenance">
              {Object.entries(cellSpec.provenance_summary)
                .map(([k, v]) => `${k}: ${v}`)
                .join(" · ")}
            </p>
          )}
        </div>
      )}

      {/* Validation results */}
      {validation && (
        <div className="subsection validation-results">
          <h3>
            Validation
            <span className="validation-score" style={{
              color: validation.overall_score >= 0.7 ? "#34d399"
                : validation.overall_score >= 0.4 ? "#fbbf24"
                : "#f87171",
            }}>
              {(validation.overall_score * 100).toFixed(0)}% pass rate
            </span>
          </h3>
          {validation.doubling_time_hours != null && (
            <p className="validation-doubling">
              Doubling time: <strong>{validation.doubling_time_hours.toFixed(1)}h</strong>
              {" "}(expected ~2h)
            </p>
          )}
          <div className="validation-checks">
            {validation.checks.map((check, i) => (
              <div key={i} className={`validation-check ${check.passed ? "check-pass" : "check-fail"}`}>
                <span className="check-icon">{check.passed ? "\u2713" : "\u2717"}</span>
                <span className="check-name">{check.name}</span>
                {check.actual && <span className="check-details">{check.actual}</span>}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function PredictedTable({
  title,
  genes,
  source,
  predictions,
  selectGene,
}: {
  title: string;
  genes: GenomeGene[];
  source: PredictionSource;
  predictions: Map<string, import("../types").FunctionalPrediction>;
  selectGene: (g: GenomeGene) => void;
}) {
  const badge = SOURCE_BADGE[source];
  return (
    <div className="subsection">
      <h3>
        <SourceBadge source={source} /> {title} ({genes.length})
      </h3>
      <div className="gene-table-scroll">
        <table className="data-table">
          <thead>
            <tr>
              <th>Locus Tag</th>
              <th>Predicted Function</th>
              <th>Confidence</th>
              <th>Tier</th>
            </tr>
          </thead>
          <tbody>
            {genes
              .sort((a, b) => {
                const predA = predictions.get(a.locus_tag);
                const predB = predictions.get(b.locus_tag);
                return (predB?.convergence?.confidence_tier ?? 4) - (predA?.convergence?.confidence_tier ?? 4) || 0;
              })
              .slice(0, 50)
              .map((g) => {
                const pred = predictions.get(g.locus_tag);
                return (
                  <tr
                    key={g.locus_tag}
                    className="clickable-row"
                    onClick={() => selectGene(g)}
                  >
                    <td style={{ color: badge?.color ?? "#94a3b8" }}>{g.locus_tag}</td>
                    <td className="pred-cell">{pred?.predicted_function || g.product}</td>
                    <td>
                      <span style={{
                        color: pred?.confidence === "high" ? "#34d399"
                          : pred?.confidence === "medium" ? "#fbbf24"
                          : "#fb923c",
                      }}>
                        {pred?.confidence || "—"}
                      </span>
                    </td>
                    <td>
                      {pred?.convergence?.confidence_tier ? (
                        <span className={`tier-badge tier-${pred.convergence.confidence_tier}`}>
                          T{pred.convergence.confidence_tier}
                        </span>
                      ) : "—"}
                    </td>
                  </tr>
                );
              })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
