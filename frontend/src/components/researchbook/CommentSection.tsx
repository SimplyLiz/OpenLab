import { useState } from "react";
import type { CommentRecord } from "../../types/researchbook";
import { useResearchBookStore } from "../../stores/researchBookStore";

interface Props {
  threadId: number;
  comments: CommentRecord[];
}

export function CommentSection({ threadId, comments }: Props) {
  const { addComment, challengeThread } = useResearchBookStore();
  const [body, setBody] = useState("");
  const [author, setAuthor] = useState("");
  const [isChallenge, setIsChallenge] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!body.trim() || !author.trim()) return;

    if (isChallenge) {
      await challengeThread(threadId, author, body);
    } else {
      await addComment(threadId, author, body);
    }
    setBody("");
  };

  return (
    <div>
      <h2>Comments ({comments.length})</h2>

      <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
        {comments.map((c) => (
          <div
            key={c.comment_id}
            style={{
              padding: "0.75rem",
              background: c.comment_type === "challenge" ? "#fce8e6" : "#f9f9f9",
              borderRadius: 6,
              borderLeft: c.comment_type === "challenge" ? "3px solid #c5221f" : "3px solid #e0e0e0",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8rem", color: "#666" }}>
              <span>
                <strong>{c.author_name}</strong>
                {c.comment_type !== "comment" && (
                  <span style={{ marginLeft: 8, textTransform: "uppercase", fontSize: "0.7rem" }}>
                    {c.comment_type}
                  </span>
                )}
              </span>
              <span>{new Date(c.created_at).toLocaleString()}</span>
            </div>
            <p style={{ margin: "0.5rem 0 0" }}>{c.body}</p>
          </div>
        ))}
      </div>

      <form onSubmit={handleSubmit} style={{ marginTop: "1rem", display: "flex", flexDirection: "column", gap: "0.5rem" }}>
        <input
          type="text"
          value={author}
          onChange={(e) => setAuthor(e.target.value)}
          placeholder="Your name"
          style={{ padding: "6px 8px", border: "1px solid #ccc", borderRadius: 4 }}
          required
        />
        <textarea
          value={body}
          onChange={(e) => setBody(e.target.value)}
          placeholder="Add a comment..."
          rows={3}
          style={{ padding: "6px 8px", border: "1px solid #ccc", borderRadius: 4, resize: "vertical" }}
          required
        />
        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
          <label style={{ fontSize: "0.85rem", display: "flex", alignItems: "center", gap: 4 }}>
            <input
              type="checkbox"
              checked={isChallenge}
              onChange={(e) => setIsChallenge(e.target.checked)}
            />
            Challenge a claim
          </label>
          <button
            type="submit"
            style={{
              marginLeft: "auto",
              padding: "6px 14px",
              background: isChallenge ? "#c5221f" : "#1a73e8",
              color: "white",
              border: "none",
              borderRadius: 4,
              cursor: "pointer",
            }}
          >
            {isChallenge ? "Submit Challenge" : "Comment"}
          </button>
        </div>
      </form>
    </div>
  );
}
