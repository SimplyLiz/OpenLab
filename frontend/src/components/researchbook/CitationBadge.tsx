interface Props {
  label: string;
  variant?: "primary" | "secondary" | "citation";
}

const STYLES: Record<string, { bg: string; fg: string }> = {
  primary: { bg: "#e8f0fe", fg: "#1a73e8" },
  secondary: { bg: "#f0f0f0", fg: "#555" },
  citation: { bg: "#fef7e0", fg: "#b05a00" },
};

export function CitationBadge({ label, variant = "primary" }: Props) {
  const style = STYLES[variant] || STYLES.primary;

  return (
    <span
      style={{
        display: "inline-block",
        padding: "1px 6px",
        borderRadius: 3,
        fontSize: "0.75rem",
        fontWeight: 500,
        background: style.bg,
        color: style.fg,
        whiteSpace: "nowrap",
      }}
    >
      {label}
    </span>
  );
}
