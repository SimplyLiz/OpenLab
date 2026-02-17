import { useState, useCallback } from "react";
import { useGeneStore } from "../../store";
import { useKnockout } from "../../hooks/useKnockout";

export function KnockoutLab() {
  const genome = useGeneStore((s) => s.genome);
  const essentiality = useGeneStore((s) => s.essentiality);
  const knockoutSet = useGeneStore((s) => s.knockoutSet);
  const setKnockoutSet = useGeneStore((s) => s.setKnockoutSet);

  const { runKnockout, isRunning } = useKnockout();
  const [filter, setFilter] = useState("");

  // Get non-essential genes (candidates for knockout)
  const candidates = (genome?.genes ?? []).filter((g) => {
    if (essentiality?.predictions) {
      return essentiality.predictions[g.locus_tag] === false;
    }
    return true; // If no essentiality data, show all
  });

  const filtered = filter.trim()
    ? candidates.filter(
        (g) =>
          g.locus_tag.toLowerCase().includes(filter.toLowerCase()) ||
          g.gene_name.toLowerCase().includes(filter.toLowerCase()) ||
          g.product.toLowerCase().includes(filter.toLowerCase()),
      )
    : candidates;

  const toggleGene = useCallback(
    (locusTag: string) => {
      const next = new Set(knockoutSet);
      if (next.has(locusTag)) {
        next.delete(locusTag);
      } else {
        next.add(locusTag);
      }
      setKnockoutSet(next);
    },
    [knockoutSet, setKnockoutSet],
  );

  const resetWT = useCallback(() => {
    setKnockoutSet(new Set());
    useGeneStore.getState().setKnockoutSimResult(null);
  }, [setKnockoutSet]);

  return (
    <div className="glass-panel knockout-lab">
      <h3 className="glass-panel-title">Knockout Lab</h3>

      <input
        type="text"
        className="knockout-search"
        placeholder="Filter genes..."
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
      />

      <div className="knockout-list">
        {filtered.slice(0, 50).map((g) => (
          <label key={g.locus_tag} className="knockout-item">
            <input
              type="checkbox"
              checked={knockoutSet.has(g.locus_tag)}
              onChange={() => toggleGene(g.locus_tag)}
            />
            <span className="knockout-tag">{g.locus_tag}</span>
            <span className="knockout-name">{g.gene_name || g.product || ""}</span>
          </label>
        ))}
        {filtered.length === 0 && (
          <div className="knockout-empty">No matching genes</div>
        )}
      </div>

      <div className="knockout-actions">
        <button
          className="knockout-btn knockout-run"
          onClick={runKnockout}
          disabled={knockoutSet.size === 0 || isRunning}
        >
          {isRunning ? "Simulating..." : `Run KO Sim (${knockoutSet.size})`}
        </button>
        <button
          className="knockout-btn knockout-reset"
          onClick={resetWT}
          disabled={knockoutSet.size === 0 && !isRunning}
        >
          Reset WT
        </button>
      </div>

      {knockoutSet.size > 0 && (
        <div className="knockout-summary">
          {knockoutSet.size} gene{knockoutSet.size !== 1 ? "s" : ""} knocked out
        </div>
      )}
    </div>
  );
}
