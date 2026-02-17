import { useState, useEffect } from "react";
import { useGeneStore } from "../store";
import { useGeneAnalysis } from "../hooks/useGeneAnalysis";
import { useResearch } from "../hooks/useResearch";
import type { FunctionalPrediction, EvidenceRecord, Hypothesis, ResearchStatus } from "../types";

const SOURCE_INFO: Record<string, { label: string; color: string; bg: string; desc: string }> = {
  genbank:  { label: "GenBank",    color: "#34d399", bg: "rgba(52,211,153,0.12)", desc: "Original NCBI annotation" },
  dnasyn:   { label: "DNASyn",     color: "#fb923c", bg: "rgba(251,146,60,0.12)", desc: "DNASyn evidence pipeline" },
  curated:  { label: "Literature", color: "#2dd4bf", bg: "rgba(45,212,191,0.12)", desc: "Expert-curated from published research" },
  genelife: { label: "GeneLife",   color: "#818cf8", bg: "rgba(129,140,248,0.12)", desc: "GeneLife live analysis" },
};

const CATEGORY_LABELS: Record<string, string> = {
  gene_expression: "Gene Expression",
  cell_membrane: "Cell Membrane",
  metabolism: "Metabolism",
  genome_preservation: "Genome Preservation",
  predicted: "Predicted Function",
  unknown: "Unknown Function",
};

const SOURCE_LABELS: Record<string, string> = {
  protein_features: "Protein Properties",
  cdd: "CDD Domains",
  ncbi_blast: "BLAST Homology",
  interpro: "InterPro",
  string: "STRING Network",
  uniprot: "UniProt",
  literature: "Literature",
};

const TIER_LABELS: Record<number, { label: string; color: string }> = {
  1: { label: "HIGH", color: "#34d399" },
  2: { label: "MODERATE", color: "#fbbf24" },
  3: { label: "LOW", color: "#fb923c" },
  4: { label: "FLAGGED", color: "#f87171" },
};

export function GeneDetail() {
  const {
    selectedGene, selectGene, predictions, essentiality, kinetics, cellSpec,
    geneAnalysisStatus, geneAnalysisProgress, geneAnalysisMessage, geneAnalysisTarget,
    researchStatus,
  } = useGeneStore();
  const { analyzeGene } = useGeneAnalysis();
  const { fetchResearch, approveGene, rejectGene, correctGene } = useResearch();
  const [correctInput, setCorrectInput] = useState("");
  const [showCorrectForm, setShowCorrectForm] = useState(false);
  const [actionPending, setActionPending] = useState(false);
  const [showStoredEvidence, setShowStoredEvidence] = useState(false);

  const g = selectedGene;

  // Fetch research status when gene changes
  useEffect(() => {
    if (g) {
      fetchResearch(g.locus_tag);
    }
  }, [g?.locus_tag, fetchResearch]);

  if (!g) return null;

  const research: ResearchStatus | undefined = researchStatus.get(g.locus_tag);
  const prediction = predictions.get(g.locus_tag);
  const isBeingAnalyzed = geneAnalysisTarget === g.locus_tag && geneAnalysisStatus === "running";
  const canReanalyze = g.functional_category === "unknown" || g.is_hypothetical;
  const isEssential = essentiality?.predictions[g.locus_tag];
  const geneKinetics = kinetics?.kinetics?.find(
    (k: { reaction_id: string }) => k.reaction_id === `rxn_${g.locus_tag}`
  );
  const csGene = cellSpec?.genes?.find(
    (cg: { locus_tag: string }) => cg.locus_tag === g.locus_tag
  );

  return (
    <div className="panel gene-detail">
      <div className="gene-detail-header">
        <h2 className="panel-title">
          <span style={{ color: g.color }}>{g.locus_tag}</span>
          {g.gene_name && <span className="gene-name">{g.gene_name}</span>}
        </h2>
        <button className="close-btn" onClick={() => selectGene(null)}>X</button>
      </div>

      {/* Source badge — prominent indicator of where annotation comes from */}
      {g.prediction_source && SOURCE_INFO[g.prediction_source] && (
        <div
          className="source-indicator"
          style={{
            borderLeftColor: SOURCE_INFO[g.prediction_source].color,
            backgroundColor: SOURCE_INFO[g.prediction_source].bg,
          }}
        >
          <span className="source-badge" style={{
            color: SOURCE_INFO[g.prediction_source].color,
            backgroundColor: "transparent",
            fontWeight: 600,
          }}>
            {SOURCE_INFO[g.prediction_source].label}
          </span>
          <span className="source-desc">{SOURCE_INFO[g.prediction_source].desc}</span>
        </div>
      )}

      <div className="id-grid">
        <div className="id-tag">
          <span className="id-label">Category</span>
          <span className="id-value" style={{ color: g.color }}>
            {CATEGORY_LABELS[g.functional_category] ?? g.functional_category}
          </span>
        </div>
        <div className="id-tag">
          <span className="id-label">Position</span>
          <span className="id-value">
            {g.start.toLocaleString()}–{g.end.toLocaleString()} ({g.strand === 1 ? "+" : "-"})
          </span>
        </div>
        <div className="id-tag">
          <span className="id-label">Length</span>
          <span className="id-value">{g.protein_length} aa</span>
        </div>
      </div>

      <div className="subsection">
        <h3>Product</h3>
        <p style={{ color: g.is_hypothetical ? "#f87171" : "#e2e8f0" }}>
          {g.product || "No annotation"}
          {g.is_hypothetical && <span className="mystery-badge">MYSTERY</span>}
        </p>
      </div>

      {/* Deep analysis progress */}
      {isBeingAnalyzed && (
        <div className="gene-analysis-progress">
          <h3>Analyzing...</h3>
          <div className="gene-analysis-bar">
            <div
              className="gene-analysis-fill"
              style={{ width: `${Math.max(geneAnalysisProgress * 100, 2)}%` }}
            />
          </div>
          <p className="gene-analysis-msg">{geneAnalysisMessage}</p>
        </div>
      )}

      {/* Re-analyze button for unknown genes that already have data */}
      {canReanalyze && !isBeingAnalyzed && prediction && prediction.evidence.length > 1 && (
        <div className="subsection">
          <button className="reanalyze-btn" onClick={() => analyzeGene(g)}>
            Re-analyze
          </button>
        </div>
      )}

      {/* Essentiality badge */}
      {isEssential !== undefined && (
        <div className="subsection">
          <span
            className="essentiality-badge"
            style={{
              color: isEssential ? "#f87171" : "#34d399",
              backgroundColor: isEssential ? "rgba(248,113,113,0.12)" : "rgba(52,211,153,0.12)",
            }}
          >
            {isEssential ? "ESSENTIAL" : "Non-essential"}
          </span>
        </div>
      )}

      {/* Enzyme kinetics */}
      {geneKinetics && (
        <div className="subsection kinetics-detail">
          <h3>Enzyme Kinetics</h3>
          <div className="kinetics-grid">
            <div className="kinetics-item">
              <span className="kinetics-label">EC</span>
              <span className="kinetics-value">{geneKinetics.ec_number}</span>
            </div>
            <div className="kinetics-item">
              <span className="kinetics-label">k<sub>cat</sub></span>
              <span className="kinetics-value">{geneKinetics.kcat.value.toFixed(2)} s<sup>-1</sup></span>
            </div>
            {Object.entries(geneKinetics.km ?? {}).slice(0, 3).map(([met, val]) => (
              <div key={met} className="kinetics-item">
                <span className="kinetics-label">K<sub>m</sub> {met}</span>
                <span className="kinetics-value">{(val as { value: number }).value.toFixed(3)} mM</span>
              </div>
            ))}
            <div className="kinetics-item">
              <span className="kinetics-label">Source</span>
              <span className="kinetics-value kinetics-source">{geneKinetics.source}</span>
            </div>
            <div className="kinetics-item">
              <span className="kinetics-label">Trust</span>
              <span className="kinetics-value" style={{
                color: geneKinetics.trust_level === "measured" ? "#34d399"
                  : geneKinetics.trust_level === "computed" ? "#fbbf24"
                  : "#fb923c",
              }}>
                {geneKinetics.trust_level}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Copy number from CellSpec */}
      {csGene && csGene.expression_rate != null && (
        <div className="subsection">
          <h3>CellSpec</h3>
          <div className="kinetics-grid">
            <div className="kinetics-item">
              <span className="kinetics-label">Expression rate</span>
              <span className="kinetics-value">{csGene.expression_rate.toFixed(4)}</span>
            </div>
          </div>
        </div>
      )}

      {/* Convergence + Hypothesis section */}
      {prediction && <PredictionPanel prediction={prediction} />}

      {/* Research Actions (DB-backed) */}
      <ResearchActionsPanel
        research={research}
        prediction={prediction}
        actionPending={actionPending}
        showCorrectForm={showCorrectForm}
        correctInput={correctInput}
        showStoredEvidence={showStoredEvidence}
        onApprove={async () => {
          setActionPending(true);
          await approveGene(g.locus_tag);
          setActionPending(false);
        }}
        onReject={async () => {
          setActionPending(true);
          await rejectGene(g.locus_tag);
          setActionPending(false);
        }}
        onCorrectToggle={() => setShowCorrectForm(!showCorrectForm)}
        onCorrectInput={setCorrectInput}
        onCorrectSubmit={async () => {
          if (!correctInput.trim()) return;
          setActionPending(true);
          await correctGene(g.locus_tag, correctInput.trim());
          setActionPending(false);
          setShowCorrectForm(false);
          setCorrectInput("");
        }}
        onToggleEvidence={() => setShowStoredEvidence(!showStoredEvidence)}
      />

      {g.protein_sequence && (
        <div className="subsection">
          <h3>Protein Sequence</h3>
          <div className="sequence-block">
            {g.protein_sequence.match(/.{1,60}/g)?.map((line, i) => (
              <div key={i} className="seq-line">
                <span className="seq-pos">{(i * 60 + 1).toString().padStart(4)}</span>
                {line.split("").map((aa, j) => (
                  <span key={j} className={`aa aa-${getAAClass(aa)}`}>{aa}</span>
                ))}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function PredictionPanel({ prediction }: { prediction: FunctionalPrediction }) {
  const conv = prediction.convergence;
  const tier = TIER_LABELS[conv.confidence_tier] || TIER_LABELS[3];

  return (
    <>
      {/* Convergence Score */}
      <div className="subsection convergence-section">
        <h3>Convergence Analysis</h3>
        <div className="convergence-bar-container">
          <div className="convergence-meter">
            <div
              className="convergence-fill"
              style={{
                width: `${Math.min(conv.score * 100, 100)}%`,
                backgroundColor: tier.color,
              }}
            />
          </div>
          <div className="convergence-stats">
            <span className="conv-score">{(conv.score * 100).toFixed(1)}%</span>
            <span className="conv-tier" style={{ color: tier.color }}>
              Tier {conv.confidence_tier}: {tier.label}
            </span>
            <span className="conv-sources">{conv.n_evidence_sources} sources</span>
          </div>
        </div>
      </div>

      {/* LLM Hypothesis */}
      {prediction.hypothesis && (
        <HypothesisPanel hypothesis={prediction.hypothesis} />
      )}

      {/* Evidence Summary */}
      {prediction.evidence_summary.length > 0 && (
        <div className="subsection">
          <h3>Evidence Summary</h3>
          <ul className="evidence-summary-list">
            {prediction.evidence_summary.map((line, i) => (
              <li key={i}>{line}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Evidence Sources */}
      {prediction.evidence.length > 0 && (
        <div className="subsection">
          <h3>Evidence Sources ({prediction.evidence.length})</h3>
          <div className="evidence-sources">
            {prediction.evidence.map((ev, i) => (
              <EvidenceCard key={i} evidence={ev} />
            ))}
          </div>
        </div>
      )}
    </>
  );
}

function HypothesisPanel({ hypothesis }: { hypothesis: Hypothesis }) {
  return (
    <div className="subsection hypothesis-section">
      <h3>
        AI Hypothesis
        <span className="hypothesis-confidence">
          confidence: {(hypothesis.confidence_score * 100).toFixed(0)}%
        </span>
      </h3>
      <div className="hypothesis-function">
        {hypothesis.predicted_function || "No prediction generated"}
      </div>
      {hypothesis.suggested_category && (
        <div className="hypothesis-category">
          Suggested: {CATEGORY_LABELS[hypothesis.suggested_category] || hypothesis.suggested_category}
        </div>
      )}
    </div>
  );
}

function EvidenceCard({ evidence }: { evidence: EvidenceRecord }) {
  const sourceLabel = SOURCE_LABELS[evidence.source] || evidence.source;
  const hasGO = evidence.go_terms.length > 0;
  const hasEC = evidence.ec_numbers.length > 0;
  const hasCats = evidence.categories.length > 0;

  return (
    <div className="evidence-card">
      <div className="evidence-source">{sourceLabel}</div>
      {hasGO && (
        <div className="evidence-terms">
          <span className="term-label">GO:</span>
          {evidence.go_terms.slice(0, 5).map((t) => (
            <span key={t} className="term-chip go-chip">{t}</span>
          ))}
          {evidence.go_terms.length > 5 && (
            <span className="term-more">+{evidence.go_terms.length - 5}</span>
          )}
        </div>
      )}
      {hasEC && (
        <div className="evidence-terms">
          <span className="term-label">EC:</span>
          {evidence.ec_numbers.map((ec) => (
            <span key={ec} className="term-chip ec-chip">{ec}</span>
          ))}
        </div>
      )}
      {hasCats && (
        <div className="evidence-terms">
          <span className="term-label">Categories:</span>
          {evidence.categories.slice(0, 3).map((c) => (
            <span key={c} className="term-chip cat-chip">{c}</span>
          ))}
        </div>
      )}
      {!hasGO && !hasEC && !hasCats && evidence.keywords.length > 0 && (
        <div className="evidence-terms">
          <span className="term-label">Keywords:</span>
          {evidence.keywords.slice(0, 5).map((k) => (
            <span key={k} className="term-chip kw-chip">{k}</span>
          ))}
        </div>
      )}
    </div>
  );
}

const RESEARCH_BADGE: Record<string, { label: string; color: string }> = {
  not_stored: { label: "Not Stored", color: "#64748b" },
  stored: { label: "Stored", color: "#60a5fa" },
  review: { label: "Under Review", color: "#fbbf24" },
  graduated: { label: "Graduated", color: "#34d399" },
  rejected: { label: "Rejected", color: "#f87171" },
};

function getResearchBadge(research: ResearchStatus | undefined) {
  if (!research) return RESEARCH_BADGE.not_stored;
  if (research.graduated) return RESEARCH_BADGE.graduated;
  if (research.hypothesis?.status === "REJECTED") return RESEARCH_BADGE.rejected;
  if (research.hypothesis) return RESEARCH_BADGE.review;
  if (research.stored) return RESEARCH_BADGE.stored;
  return RESEARCH_BADGE.not_stored;
}

function ResearchActionsPanel({
  research, prediction, actionPending, showCorrectForm, correctInput, showStoredEvidence,
  onApprove, onReject, onCorrectToggle, onCorrectInput, onCorrectSubmit, onToggleEvidence,
}: {
  research: ResearchStatus | undefined;
  prediction: FunctionalPrediction | undefined;
  actionPending: boolean;
  showCorrectForm: boolean;
  correctInput: string;
  showStoredEvidence: boolean;
  onApprove: () => void;
  onReject: () => void;
  onCorrectToggle: () => void;
  onCorrectInput: (v: string) => void;
  onCorrectSubmit: () => void;
  onToggleEvidence: () => void;
}) {
  const badge = getResearchBadge(research);
  const hasHypothesis = !!research?.hypothesis;
  const evidenceCount = research?.evidence?.length ?? 0;

  return (
    <div className="subsection research-actions-section">
      <h3>
        Research Status
        <span className="research-badge" style={{ color: badge.color, borderColor: badge.color }}>
          {badge.label}
        </span>
      </h3>

      {/* DB convergence (if different from pipeline) */}
      {research && research.convergence_score > 0 && (
        <div className="research-convergence">
          <div className="convergence-meter" style={{ height: 6 }}>
            <div
              className="convergence-fill"
              style={{
                width: `${Math.min(research.convergence_score * 100, 100)}%`,
                backgroundColor: (TIER_LABELS[research.tier] || TIER_LABELS[3]).color,
              }}
            />
          </div>
          <span className="research-conv-label">
            DB Convergence: {(research.convergence_score * 100).toFixed(1)}%
            {research.disagreement_count > 0 && (
              <span className="disagree-flag"> ({research.disagreement_count} disagreements)</span>
            )}
          </span>
        </div>
      )}

      {/* Proposed function */}
      {research?.proposed_function && (
        <div className="research-proposed-fn">
          <span className="fn-label">Function:</span> {research.proposed_function}
        </div>
      )}

      {/* Stored evidence count */}
      {evidenceCount > 0 && (
        <div className="research-evidence-count" onClick={onToggleEvidence} style={{ cursor: "pointer" }}>
          {evidenceCount} evidence record{evidenceCount !== 1 ? "s" : ""} in database
          <span className="toggle-icon">{showStoredEvidence ? " ▾" : " ▸"}</span>
        </div>
      )}
      {showStoredEvidence && research?.evidence && (
        <div className="stored-evidence-list">
          {research.evidence.map((ev) => (
            <div key={ev.evidence_id} className="stored-evidence-item">
              <span className="se-type">{ev.evidence_type}</span>
              <span className="se-ref">{ev.source_ref || "—"}</span>
              {ev.confidence != null && (
                <span className="se-conf">{(ev.confidence * 100).toFixed(0)}%</span>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Action buttons */}
      {(hasHypothesis || prediction?.hypothesis) && !research?.graduated && (
        <div className="research-action-btns">
          <button
            className="research-btn approve-btn"
            onClick={onApprove}
            disabled={actionPending}
          >
            Approve
          </button>
          <button
            className="research-btn reject-btn"
            onClick={onReject}
            disabled={actionPending}
          >
            Reject
          </button>
          <button
            className="research-btn correct-btn"
            onClick={onCorrectToggle}
            disabled={actionPending}
          >
            Correct
          </button>
        </div>
      )}

      {showCorrectForm && (
        <div className="correct-form">
          <input
            type="text"
            className="correct-input"
            placeholder="Enter corrected function..."
            value={correctInput}
            onChange={(e) => onCorrectInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && onCorrectSubmit()}
          />
          <button className="research-btn approve-btn" onClick={onCorrectSubmit} disabled={actionPending || !correctInput.trim()}>
            Submit
          </button>
        </div>
      )}
    </div>
  );
}

function getAAClass(aa: string): string {
  if ("DE".includes(aa)) return "neg";
  if ("KRH".includes(aa)) return "pos";
  if ("AILMFWVP".includes(aa)) return "hydro";
  if ("STYCNQG".includes(aa)) return "polar";
  return "other";
}
