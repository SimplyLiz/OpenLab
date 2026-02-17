import { useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { useResearchBookStore } from "../stores/researchBookStore";

export function ForkPage() {
  const { threadId } = useParams<{ threadId: string }>();
  const navigate = useNavigate();
  const forkThread = useResearchBookStore((s) => s.forkThread);

  const [cancerType, setCancerType] = useState("");
  const [summary, setSummary] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!threadId || !summary.trim()) return;

    setSubmitting(true);
    try {
      const childId = await forkThread(Number(threadId), cancerType, summary);
      navigate(`/research/${childId}`);
    } catch {
      setSubmitting(false);
    }
  };

  return (
    <div style={{ maxWidth: 600, margin: "0 auto", padding: "2rem 1rem" }}>
      <Link to={`/research/${threadId}`} style={{ color: "#666", textDecoration: "none" }}>
        &larr; Back to thread
      </Link>

      <h1 style={{ marginTop: "1rem" }}>Fork Thread #{threadId}</h1>
      <p style={{ color: "#666" }}>
        Create a new research thread based on this one with modified parameters.
        A new agent run will be dispatched.
      </p>

      <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
        <div>
          <label style={{ display: "block", marginBottom: "0.25rem", fontWeight: 500 }}>
            Cancer Type
          </label>
          <input
            type="text"
            value={cancerType}
            onChange={(e) => setCancerType(e.target.value)}
            placeholder="e.g., breast, colorectal, lung"
            style={{ width: "100%", padding: "8px", border: "1px solid #ccc", borderRadius: 4 }}
          />
        </div>

        <div>
          <label style={{ display: "block", marginBottom: "0.25rem", fontWeight: 500 }}>
            Modification Summary *
          </label>
          <textarea
            value={summary}
            onChange={(e) => setSummary(e.target.value)}
            placeholder="Describe what you're changing and why..."
            rows={4}
            style={{ width: "100%", padding: "8px", border: "1px solid #ccc", borderRadius: 4, resize: "vertical" }}
            required
          />
        </div>

        <button
          type="submit"
          disabled={submitting || !summary.trim()}
          style={{
            padding: "10px 20px",
            background: submitting ? "#ccc" : "#1a73e8",
            color: "white",
            border: "none",
            borderRadius: 4,
            cursor: submitting ? "default" : "pointer",
            fontSize: "1rem",
          }}
        >
          {submitting ? "Creating fork..." : "Create Fork"}
        </button>
      </form>
    </div>
  );
}
