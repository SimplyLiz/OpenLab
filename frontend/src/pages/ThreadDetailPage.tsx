import { useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { useResearchBookStore } from "../stores/researchBookStore";
import { useResearchBookStream } from "../hooks/useResearchBookStream";
import { ClaimsTable } from "../components/researchbook/ClaimsTable";
import { CommentSection } from "../components/researchbook/CommentSection";
import { ConfidenceBar } from "../components/researchbook/ConfidenceBar";

export function ThreadDetailPage() {
  const { threadId } = useParams<{ threadId: string }>();
  const tid = threadId ? Number(threadId) : null;

  const { activeThread, threadLoading, fetchThread, publishThread } =
    useResearchBookStore();

  useResearchBookStream(tid);

  useEffect(() => {
    if (tid) fetchThread(tid);
  }, [tid, fetchThread]);

  if (threadLoading || !activeThread) {
    return <div style={{ padding: "2rem" }}>Loading thread...</div>;
  }

  const t = activeThread;

  return (
    <div style={{ maxWidth: 900, margin: "0 auto", padding: "2rem 1rem" }}>
      <Link to="/research" style={{ color: "#666", textDecoration: "none" }}>
        &larr; Back to feed
      </Link>

      <div style={{ marginTop: "1rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <h1 style={{ margin: "0 0 0.5rem" }}>{t.title || `${t.gene_symbol} Research`}</h1>
            <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
              <span style={{
                padding: "2px 8px",
                borderRadius: 4,
                fontSize: "0.8rem",
                background: t.status === "published" ? "#e6f4ea" : t.status === "challenged" ? "#fce8e6" : "#f0f0f0",
                color: t.status === "published" ? "#137333" : t.status === "challenged" ? "#c5221f" : "#666",
              }}>
                {t.status}
              </span>
              <span style={{ color: "#666" }}>{t.gene_symbol}</span>
              {t.cancer_type && <span style={{ color: "#666" }}>/ {t.cancer_type}</span>}
            </div>
          </div>

          <div style={{ display: "flex", gap: "0.5rem" }}>
            {t.status === "draft" && (
              <button onClick={() => tid && publishThread(tid)}
                style={{ padding: "6px 12px", background: "#1a73e8", color: "white", border: "none", borderRadius: 4, cursor: "pointer" }}>
                Publish
              </button>
            )}
            <Link to={`/research/${tid}/fork`}
              style={{ padding: "6px 12px", background: "#f0f0f0", border: "1px solid #ccc", borderRadius: 4, textDecoration: "none", color: "#333" }}>
              Fork
            </Link>
          </div>
        </div>

        {t.convergence_score !== undefined && (
          <div style={{ marginTop: "1rem" }}>
            <ConfidenceBar score={t.convergence_score} label="Convergence" />
          </div>
        )}

        {t.summary && (
          <div style={{ marginTop: "1.5rem" }}>
            <h2>Summary</h2>
            <p>{t.summary}</p>
          </div>
        )}

        {t.claims_snapshot && t.claims_snapshot.length > 0 && (
          <div style={{ marginTop: "1.5rem" }}>
            <h2>Claims ({t.claims_snapshot.length})</h2>
            <ClaimsTable claims={t.claims_snapshot} />
          </div>
        )}

        {t.forked_from_id && (
          <div style={{ marginTop: "1rem", padding: "0.5rem", background: "#f9f9f9", borderRadius: 4 }}>
            Forked from{" "}
            <Link to={`/research/${t.forked_from_id}`}>Thread #{t.forked_from_id}</Link>
          </div>
        )}

        {t.forks && t.forks.length > 0 && (
          <div style={{ marginTop: "1.5rem" }}>
            <h2>Forks ({t.forks.length})</h2>
            {t.forks.map((f) => (
              <div key={f.fork_id} style={{ padding: "0.5rem 0", borderBottom: "1px solid #eee" }}>
                <Link to={`/research/${f.child_thread_id}`}>
                  Fork #{f.child_thread_id}
                </Link>
                {" "}&mdash; {f.modification_summary}
              </div>
            ))}
          </div>
        )}

        <div style={{ marginTop: "2rem" }}>
          <CommentSection threadId={tid!} comments={t.comments || []} />
        </div>
      </div>
    </div>
  );
}
