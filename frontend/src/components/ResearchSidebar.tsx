import { useState, useEffect, useRef } from "react";
import { useGeneStore } from "../store";
import { useResearchManager } from "../hooks/useAutoResearch";
import { useResearch } from "../hooks/useResearch";
import type { ResearchSummary } from "../types";

export function ResearchSidebar() {
  const { genome, selectGene, geneAnalysisStatus, geneAnalysisTarget } =
    useGeneStore();
  const {
    queue,
    totalQueued,
    queueLoading,
    refetchQueue,
    batchActive,
    batchCurrentGene,
    batchCompleted,
    batchTotal,
    batchProgress,
    startBatchResearch,
    stopBatchResearch,
    researchSingleGene,
  } = useResearchManager();
  const { fetchSummary } = useResearch();

  const [summary, setSummary] = useState<ResearchSummary | null>(null);
  const [tab, setTab] = useState<"queue" | "review" | "candidates" | "disagreements">("queue");
  const prevBatchActive = useRef(batchActive);

  // Fetch summary on mount
  useEffect(() => {
    fetchSummary().then((s) => {
      if (s) setSummary(s);
    });
  }, [fetchSummary]);

  // Refetch summary + queue when batch finishes
  useEffect(() => {
    if (prevBatchActive.current && !batchActive) {
      fetchSummary().then((s) => {
        if (s) setSummary(s);
      });
      refetchQueue();
    }
    prevBatchActive.current = batchActive;
  }, [batchActive, fetchSummary, refetchQueue]);

  const handleClickGene = (locusTag: string) => {
    if (!genome) return;
    const g = genome.genes.find((gene) => gene.locus_tag === locusTag);
    if (g) selectGene(g);
  };

  const batchPct = Math.round(batchProgress * 100);

  return (
    <aside className="research-sidebar">
      <h2 className="sidebar-title">Research</h2>

      {/* Summary stats */}
      {summary && (
        <div className="sidebar-summary">
          <div className="sidebar-stat">
            <div className="sidebar-stat-num">{summary.total_stored}</div>
            <div className="sidebar-stat-label">stored</div>
          </div>
          <div className="sidebar-stat">
            <div className="sidebar-stat-num" style={{ color: "#60a5fa" }}>
              {summary.total_with_evidence}
            </div>
            <div className="sidebar-stat-label">evidence</div>
          </div>
          <div className="sidebar-stat">
            <div className="sidebar-stat-num" style={{ color: "#fbbf24" }}>
              {summary.total_with_hypothesis}
            </div>
            <div className="sidebar-stat-label">hypothesized</div>
          </div>
          <div className="sidebar-stat">
            <div className="sidebar-stat-num" style={{ color: "#34d399" }}>
              {summary.total_graduated}
            </div>
            <div className="sidebar-stat-label">graduated</div>
          </div>
          <div className="sidebar-stat">
            <div className="sidebar-stat-num" style={{ color: "#f87171" }}>
              {summary.total_unknown}
            </div>
            <div className="sidebar-stat-label">unknown</div>
          </div>
          <div className="sidebar-stat">
            <div className="sidebar-stat-num" style={{ color: "#a78bfa" }}>
              {totalQueued}
            </div>
            <div className="sidebar-stat-label">queued</div>
          </div>
        </div>
      )}

      {/* Batch button */}
      {!batchActive && totalQueued > 0 && (
        <button className="batch-research-btn" onClick={startBatchResearch}>
          Research All Unknown ({totalQueued})
        </button>
      )}

      {/* Batch progress */}
      {batchActive && (
        <div className="batch-progress">
          {batchCurrentGene && (
            <div className="batch-status">Analyzing {batchCurrentGene}</div>
          )}
          <div className="arb-track">
            <div className="arb-fill" style={{ width: `${batchPct}%` }} />
          </div>
          <div className="batch-status">
            {batchCompleted} / {batchTotal} completed ({batchPct}%)
          </div>
          <button className="cancel-batch-btn" onClick={stopBatchResearch}>
            Cancel
          </button>
        </div>
      )}

      {/* Tabs */}
      <div className="sidebar-tabs">
        <button
          className={`sidebar-tab ${tab === "queue" ? "active" : ""}`}
          onClick={() => setTab("queue")}
        >
          Queue{totalQueued > 0 ? ` (${totalQueued})` : ""}
        </button>
        <button
          className={`sidebar-tab ${tab === "review" ? "active" : ""}`}
          onClick={() => setTab("review")}
        >
          Review{summary ? ` (${summary.needs_review.length})` : ""}
        </button>
        <button
          className={`sidebar-tab ${tab === "candidates" ? "active" : ""}`}
          onClick={() => setTab("candidates")}
        >
          Grads{summary ? ` (${summary.graduation_candidates.length})` : ""}
        </button>
        <button
          className={`sidebar-tab ${tab === "disagreements" ? "active" : ""}`}
          onClick={() => setTab("disagreements")}
        >
          Conflicts{summary ? ` (${summary.disagreements.length})` : ""}
        </button>
      </div>

      {/* Tab content */}
      {tab === "queue" && (
        <div className="queue-list">
          {queueLoading && <p className="text-dim">Loading queue...</p>}
          {!queueLoading && queue.length === 0 && (
            <p className="text-dim">No unknown genes in queue</p>
          )}
          {queue.map((item) => {
            const isRunning =
              geneAnalysisTarget === item.locus_tag &&
              geneAnalysisStatus === "running";
            return (
              <div key={item.locus_tag} className="queue-item">
                <span
                  className="queue-item-tag"
                  onClick={() => handleClickGene(item.locus_tag)}
                >
                  {item.locus_tag}
                </span>
                <button
                  className="queue-analyze-btn"
                  disabled={batchActive || geneAnalysisStatus === "running"}
                  onClick={() => {
                    handleClickGene(item.locus_tag);
                    researchSingleGene(item.locus_tag);
                  }}
                >
                  {isRunning ? "..." : "Analyze"}
                </button>
              </div>
            );
          })}
        </div>
      )}

      {tab === "review" && (
        <div className="research-list">
          {!summary || summary.needs_review.length === 0 ? (
            <p className="text-dim">No genes with DRAFT hypotheses</p>
          ) : (
            summary.needs_review.map((item) => (
              <div
                key={item.locus_tag}
                className="research-list-item"
                onClick={() => handleClickGene(item.locus_tag)}
              >
                <span className="rli-tag">{item.locus_tag}</span>
                <span className="rli-title">{item.hypothesis_title}</span>
                <span className="rli-conf">
                  {((item.confidence ?? 0) * 100).toFixed(0)}%
                </span>
              </div>
            ))
          )}
        </div>
      )}

      {tab === "candidates" && (
        <div className="research-list">
          {!summary || summary.graduation_candidates.length === 0 ? (
            <p className="text-dim">No graduation candidates yet</p>
          ) : (
            summary.graduation_candidates.map((item) => (
              <div
                key={item.locus_tag}
                className="research-list-item"
                onClick={() => handleClickGene(item.locus_tag)}
              >
                <span className="rli-tag">{item.locus_tag}</span>
                <span className="rli-title">{item.proposed_function}</span>
                <span className="rli-conf" style={{ color: "#34d399" }}>
                  {((item.confidence ?? 0) * 100).toFixed(0)}%
                </span>
              </div>
            ))
          )}
        </div>
      )}

      {tab === "disagreements" && (
        <div className="research-list">
          {!summary || summary.disagreements.length === 0 ? (
            <p className="text-dim">No evidence disagreements detected</p>
          ) : (
            summary.disagreements.map((item) => (
              <div
                key={item.locus_tag}
                className="research-list-item"
                onClick={() => handleClickGene(item.locus_tag)}
              >
                <span className="rli-tag">{item.locus_tag}</span>
                <span className="rli-title" style={{ color: "#f87171" }}>
                  {item.top_disagreement}
                </span>
                <span className="rli-conf">
                  {item.disagreement_count} conflict
                  {item.disagreement_count !== 1 ? "s" : ""}
                </span>
              </div>
            ))
          )}
        </div>
      )}
    </aside>
  );
}
