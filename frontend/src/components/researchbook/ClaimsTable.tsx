import type { Claim } from "../../types/researchbook";
import { ConfidenceBar } from "./ConfidenceBar";
import { CitationBadge } from "./CitationBadge";

interface Props {
  claims: Claim[];
}

export function ClaimsTable({ claims }: Props) {
  if (!claims.length) return <p style={{ color: "#666" }}>No claims.</p>;

  return (
    <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.9rem" }}>
      <thead>
        <tr style={{ borderBottom: "2px solid #e0e0e0", textAlign: "left" }}>
          <th style={{ padding: "8px 4px" }}>Claim</th>
          <th style={{ padding: "8px 4px", width: 120 }}>Confidence</th>
          <th style={{ padding: "8px 4px", width: 100 }}>Citations</th>
          <th style={{ padding: "8px 4px", width: 80 }}>Status</th>
        </tr>
      </thead>
      <tbody>
        {claims.map((claim, i) => (
          <tr key={i} style={{ borderBottom: "1px solid #f0f0f0" }}>
            <td style={{ padding: "8px 4px" }}>
              {claim.is_speculative && (
                <span style={{ color: "#b05a00", fontSize: "0.75rem", marginRight: 4 }}>
                  [SPECULATIVE]
                </span>
              )}
              {claim.claim_text}
            </td>
            <td style={{ padding: "8px 4px" }}>
              <ConfidenceBar score={claim.confidence} />
            </td>
            <td style={{ padding: "8px 4px" }}>
              <div style={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
                {claim.citations.map((c, j) => (
                  <CitationBadge key={j} label={c} variant="citation" />
                ))}
                {claim.citations.length === 0 && (
                  <span style={{ color: "#999", fontSize: "0.75rem" }}>none</span>
                )}
              </div>
            </td>
            <td style={{ padding: "8px 4px" }}>
              <span
                style={{
                  fontSize: "0.75rem",
                  color:
                    claim.citation_status === "valid"
                      ? "#137333"
                      : claim.citation_status === "invalid"
                        ? "#c5221f"
                        : "#666",
                }}
              >
                {claim.citation_status}
              </span>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
