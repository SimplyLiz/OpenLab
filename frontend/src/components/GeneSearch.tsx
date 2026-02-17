import { useState, type FormEvent } from "react";
import { useGeneStore } from "../store";
import { usePipeline } from "../hooks/usePipeline";

const GENE_EXAMPLES = ["TP53", "BRCA1", "CFTR", "EGFR"];
const GENOME_EXAMPLES = ["JCVI-syn3.0", "JCVI-syn2.0", "JCVI-syn3A"];

export function GeneSearch() {
  const [input, setInput] = useState("");
  const { isAnalyzing, setQuery } = useGeneStore();
  const { analyze } = usePipeline();

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const q = input.trim();
    if (!q || isAnalyzing) return;
    setQuery(q);
    analyze(q);
  };

  const handleExample = (gene: string) => {
    setInput(gene);
    setQuery(gene);
    analyze(gene);
  };

  return (
    <div className="gene-search">
      <h1 className="logo">
        <span className="logo-gene">Gene</span>
        <span className="logo-life">Life</span>
      </h1>
      <p className="tagline">Drop in a gene. Understand it completely. Bring it to life.</p>

      <form onSubmit={handleSubmit} className="search-form">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Gene symbol, genome accession, or organism (e.g. TP53, JCVI-syn3.0)"
          className="search-input"
          disabled={isAnalyzing}
          autoFocus
        />
        <button type="submit" className="search-btn" disabled={isAnalyzing || !input.trim()}>
          {isAnalyzing ? "Analyzing..." : "Analyze"}
        </button>
      </form>

      <div className="examples">
        <span className="examples-label">Genes:</span>
        {GENE_EXAMPLES.map((gene) => (
          <button
            key={gene}
            className="example-chip"
            onClick={() => handleExample(gene)}
            disabled={isAnalyzing}
          >
            {gene}
          </button>
        ))}
        <span className="examples-label" style={{ marginLeft: "0.75rem" }}>Synthetic Genomes:</span>
        {GENOME_EXAMPLES.map((gene) => (
          <button
            key={gene}
            className="example-chip genome-chip"
            onClick={() => handleExample(gene)}
            disabled={isAnalyzing}
          >
            {gene}
          </button>
        ))}
      </div>
    </div>
  );
}
