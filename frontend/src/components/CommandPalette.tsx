import { useState, useEffect, useRef, useCallback, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useGeneStore } from "../store";
import { usePipeline } from "../hooks/usePipeline";

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();
  const { genome, isAnalyzing, setQuery, activeGenomeId } = useGeneStore();
  const { analyze } = usePipeline();

  // Cmd+K to toggle
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setOpen((o) => !o);
      }
      if (e.key === "Escape") {
        setOpen(false);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  // Focus input when opened
  useEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open]);

  const genes = genome?.genes ?? [];

  // Filter genes by input
  const filtered = input.trim()
    ? genes.filter(
        (g) =>
          g.locus_tag.toLowerCase().includes(input.toLowerCase()) ||
          g.gene_name.toLowerCase().includes(input.toLowerCase()) ||
          g.product.toLowerCase().includes(input.toLowerCase()),
      ).slice(0, 20)
    : [];

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const q = input.trim();
    if (!q || isAnalyzing) return;
    setQuery(q);
    analyze(q);
    setOpen(false);
    setInput("");
  };

  const handleSelectGene = useCallback(
    (locusTag: string) => {
      const gene = genes.find((g) => g.locus_tag === locusTag);
      if (gene) {
        useGeneStore.getState().selectGene(gene);
        if (activeGenomeId) {
          navigate(`/g/${activeGenomeId}/map`);
        }
      }
      setOpen(false);
      setInput("");
    },
    [genes, activeGenomeId, navigate],
  );

  if (!open) return null;

  return (
    <div className="command-palette-overlay" onClick={() => setOpen(false)}>
      <div className="command-palette" onClick={(e) => e.stopPropagation()}>
        <form onSubmit={handleSubmit} className="command-palette-form">
          <span className="command-palette-icon">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
              <circle cx="7" cy="7" r="5" />
              <line x1="11" y1="11" x2="14" y2="14" />
            </svg>
          </span>
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Search genes, navigate, or analyze..."
            className="command-palette-input"
          />
          <kbd className="command-palette-kbd">esc</kbd>
        </form>

        {filtered.length > 0 && (
          <div className="command-palette-results">
            {filtered.map((g) => (
              <button
                key={g.locus_tag}
                className="command-palette-result"
                onClick={() => handleSelectGene(g.locus_tag)}
              >
                <span className="command-palette-result-tag">{g.locus_tag}</span>
                <span className="command-palette-result-name">
                  {g.gene_name || g.product || "Unknown"}
                </span>
                <span
                  className="command-palette-result-dot"
                  style={{ background: g.color }}
                />
              </button>
            ))}
          </div>
        )}

        {input.trim() && filtered.length === 0 && (
          <div className="command-palette-empty">
            <p>No matching genes. Press Enter to run a full analysis.</p>
          </div>
        )}
      </div>
    </div>
  );
}
