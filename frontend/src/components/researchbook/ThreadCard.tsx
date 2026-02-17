import type { ResearchThreadSummary } from "../../types/researchbook";
import { ConfidenceBar } from "./ConfidenceBar";
import { CitationBadge } from "./CitationBadge";

interface Props {
  thread: ResearchThreadSummary;
}

const STATUS_COLORS: Record<string, { bg: string; fg: string }> = {
  draft: { bg: "#f0f0f0", fg: "#666" },
  published: { bg: "#e6f4ea", fg: "#137333" },
  challenged: { bg: "#fce8e6", fg: "#c5221f" },
  superseded: { bg: "#fef7e0", fg: "#b05a00" },
  archived: { bg: "#e8e8e8", fg: "#999" },
};

export function ThreadCard({ thread }: Props) {
  const statusStyle = STATUS_COLORS[thread.status] || STATUS_COLORS.draft;

  return (
    <div
      style={{
        border: "1px solid #e0e0e0",
        borderRadius: 8,
        padding: "1rem 1.25rem",
        background: "white",
        cursor: "pointer",
        transition: "box-shadow 0.15s",
      }}
      onMouseEnter={(e) => (e.currentTarget.style.boxShadow = "0 2px 8px rgba(0,0,0,0.1)")}
      onMouseLeave={(e) => (e.currentTarget.style.boxShadow = "none")}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <h3 style={{ margin: "0 0 0.25rem" }}>
            {thread.title || `${thread.gene_symbol} Research`}
          </h3>
          <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", fontSize: "0.85rem" }}>
            <CitationBadge label={thread.gene_symbol} />
            {thread.cancer_type && <CitationBadge label={thread.cancer_type} variant="secondary" />}
            <span
              style={{
                padding: "1px 6px",
                borderRadius: 3,
                fontSize: "0.75rem",
                background: statusStyle.bg,
                color: statusStyle.fg,
              }}
            >
              {thread.status}
            </span>
          </div>
        </div>
        <div style={{ textAlign: "right", fontSize: "0.8rem", color: "#666" }}>
          <div>{new Date(thread.created_at).toLocaleDateString()}</div>
        </div>
      </div>

      {thread.convergence_score !== undefined && thread.convergence_score > 0 && (
        <div style={{ marginTop: "0.75rem" }}>
          <ConfidenceBar score={thread.convergence_score} label="Convergence" />
        </div>
      )}

      <div style={{ display: "flex", gap: "1rem", marginTop: "0.75rem", fontSize: "0.8rem", color: "#666" }}>
        <span>{thread.comment_count} comments</span>
        <span>{thread.challenge_count} challenges</span>
        <span>{thread.fork_count} forks</span>
      </div>
    </div>
  );
}
