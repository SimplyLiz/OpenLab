interface Props {
  score: number; // 0-1
  label?: string;
}

function scoreColor(score: number): string {
  if (score >= 0.7) return "#137333";
  if (score >= 0.4) return "#b05a00";
  return "#c5221f";
}

export function ConfidenceBar({ score, label }: Props) {
  const pct = Math.round(score * 100);
  const color = scoreColor(score);

  return (
    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
      {label && <span style={{ fontSize: "0.75rem", color: "#666", minWidth: 80 }}>{label}</span>}
      <div
        style={{
          flex: 1,
          height: 6,
          background: "#e8e8e8",
          borderRadius: 3,
          overflow: "hidden",
        }}
      >
        <div
          style={{
            width: `${pct}%`,
            height: "100%",
            background: color,
            borderRadius: 3,
            transition: "width 0.3s",
          }}
        />
      </div>
      <span style={{ fontSize: "0.75rem", color, fontWeight: 600, minWidth: 35, textAlign: "right" }}>
        {pct}%
      </span>
    </div>
  );
}
