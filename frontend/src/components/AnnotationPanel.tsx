import { useGeneStore } from "../store";

export function AnnotationPanel() {
  const { annotation } = useGeneStore();
  if (!annotation) return null;

  const { function_summary, go_terms, diseases, pathways, drugs, pubmed_count } = annotation;

  // Group GO terms by category
  const goByCategory = go_terms.reduce(
    (acc, term) => {
      const cat = term.category || "unknown";
      (acc[cat] ??= []).push(term);
      return acc;
    },
    {} as Record<string, typeof go_terms>
  );

  const categoryLabels: Record<string, string> = {
    molecular_function: "Molecular Function",
    biological_process: "Biological Process",
    cellular_component: "Cellular Component",
    unknown: "Other",
  };

  return (
    <div className="panel annotation-panel">
      <h2 className="panel-title">Annotation & Function</h2>

      {function_summary && (
        <div className="subsection">
          <h3>Function</h3>
          <p>{function_summary}</p>
        </div>
      )}

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-value">{pubmed_count.toLocaleString()}</div>
          <div className="stat-label">PubMed articles</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{go_terms.length}</div>
          <div className="stat-label">GO terms</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{diseases.length}</div>
          <div className="stat-label">Disease links</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{pathways.length}</div>
          <div className="stat-label">Pathways</div>
        </div>
      </div>

      {/* GO Terms by category */}
      {Object.entries(goByCategory).map(([cat, terms]) => (
        <div key={cat} className="subsection">
          <h3>{categoryLabels[cat] ?? cat}</h3>
          <div className="tag-list">
            {terms.slice(0, 15).map((t) => (
              <span key={t.go_id} className="go-tag" title={`${t.go_id} [${t.evidence}]`}>
                {t.name}
              </span>
            ))}
            {terms.length > 15 && (
              <span className="more-tag">+{terms.length - 15} more</span>
            )}
          </div>
        </div>
      ))}

      {/* Diseases */}
      {diseases.length > 0 && (
        <div className="subsection">
          <h3>Disease Associations</h3>
          <ul className="disease-list">
            {diseases.map((d, i) => (
              <li key={i}>
                <strong>{d.disease}</strong>
                <span className="source-badge">{d.source}</span>
                {d.mim_id && <span className="mim-id">MIM:{d.mim_id}</span>}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Pathways */}
      {pathways.length > 0 && (
        <div className="subsection">
          <h3>Pathways</h3>
          <div className="tag-list">
            {pathways.map((p) => (
              <span key={p.pathway_id} className="pathway-tag" title={p.pathway_id}>
                {p.name}
                <span className="source-badge small">{p.source}</span>
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Drug targets */}
      {drugs.length > 0 && (
        <div className="subsection">
          <h3>Drug Targets</h3>
          <ul className="drug-list">
            {drugs.map((d, i) => (
              <li key={i}>
                <strong>{d.drug_name}</strong>
                {d.action && <span className="drug-action">{d.action}</span>}
                {d.status && <span className="source-badge">{d.status}</span>}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
