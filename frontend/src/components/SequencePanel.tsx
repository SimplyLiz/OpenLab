import { useGeneStore } from "../store";

export function SequencePanel() {
  const { sequenceAnalysis } = useGeneStore();
  if (!sequenceAnalysis) return null;

  const { primary_orf, cai, gc_profile, cpg_islands, splice_sites, seq_length, codon_usage } =
    sequenceAnalysis;

  // Top 10 most-used codons
  const topCodons = [...codon_usage].sort((a, b) => b.count - a.count).slice(0, 10);

  return (
    <div className="panel sequence-panel">
      <h2 className="panel-title">Sequence Analysis</h2>

      <div className="stats-grid">
        <StatCard label="Length" value={`${seq_length.toLocaleString()} bp`} />
        <StatCard label="GC Content" value={`${gc_profile.overall}%`} />
        <StatCard label="CAI" value={cai.toFixed(3)} sub="Codon Adaptation Index" />
        <StatCard label="CpG Islands" value={String(cpg_islands.length)} />
        <StatCard label="Splice Sites" value={String(splice_sites.length)} sub="high-confidence" />
      </div>

      {primary_orf && (
        <div className="subsection">
          <h3>Primary ORF</h3>
          <p>
            Position {primary_orf.start}–{primary_orf.end} (frame {primary_orf.frame}),{" "}
            <strong>{primary_orf.length_aa} amino acids</strong>
          </p>
        </div>
      )}

      {gc_profile.profile.length > 0 && (
        <div className="subsection">
          <h3>GC Content Profile</h3>
          <div className="gc-sparkline">
            {gc_profile.profile.map((gc, i) => (
              <div
                key={i}
                className="gc-bar"
                style={{
                  height: `${gc}%`,
                  backgroundColor: gc > 60 ? "#e74c3c" : gc > 40 ? "#3498db" : "#95a5a6",
                }}
                title={`Window ${i}: ${gc}% GC`}
              />
            ))}
          </div>
          <p className="gc-legend">
            {gc_profile.profile.length} windows of {gc_profile.window_size} bp
          </p>
        </div>
      )}

      {cpg_islands.length > 0 && (
        <div className="subsection">
          <h3>CpG Islands</h3>
          <table className="data-table">
            <thead>
              <tr><th>Start</th><th>End</th><th>Length</th><th>GC%</th><th>Obs/Exp</th></tr>
            </thead>
            <tbody>
              {cpg_islands.map((island, i) => (
                <tr key={i}>
                  <td>{island.start.toLocaleString()}</td>
                  <td>{island.end.toLocaleString()}</td>
                  <td>{island.length}</td>
                  <td>{island.gc_percent}%</td>
                  <td>{island.obs_exp_ratio}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {topCodons.length > 0 && (
        <div className="subsection">
          <h3>Top Codons</h3>
          <div className="codon-grid">
            {topCodons.map((c) => (
              <div key={c.codon} className="codon-item">
                <code>{c.codon}</code>
                <span className="codon-aa">{c.amino_acid}</span>
                <span className="codon-count">{c.count}x</span>
                <span className="codon-rscu">RSCU {c.rscu}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function StatCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="stat-card">
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
      {sub && <div className="stat-sub">{sub}</div>}
    </div>
  );
}
