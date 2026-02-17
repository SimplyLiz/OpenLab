import { useEffect, useState, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useGenomes } from "../hooks/useGenomes";
import type { GenomeSummary } from "../types";

interface NCBIResult {
  accession: string;
  organism: string;
  title: string;
  length: number;
}

export function GenomeSelectorPage() {
  const navigate = useNavigate();
  const { genomes, fetchGenomes, selectGenome, searchNCBI, fetchGenome } = useGenomes();
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<NCBIResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [importing, setImporting] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    fetchGenomes();
  }, [fetchGenomes]);


  const handleSearch = useCallback(
    (query: string) => {
      setSearchQuery(query);
      setError(null);
      if (debounceRef.current) clearTimeout(debounceRef.current);
      if (query.length < 2) {
        setSearchResults([]);
        setSearching(false);
        return;
      }
      setSearching(true);
      debounceRef.current = setTimeout(async () => {
        try {
          const results = await searchNCBI(query);
          setSearchResults(results);
        } catch {
          setSearchResults([]);
        } finally {
          setSearching(false);
        }
      }, 300);
    },
    [searchNCBI],
  );

  const handleImport = async (accession: string) => {
    setImporting(accession);
    setError(null);
    try {
      const result = await fetchGenome(accession);
      await fetchGenomes();
      if (result.genome_id) {
        selectGenome(result.genome_id);
      }
    } catch (err: any) {
      setError(`Import failed for ${accession}`);
    } finally {
      setImporting(null);
    }
  };

  const fmtBp = (n: number) => {
    if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2)} Mbp`;
    if (n >= 1_000) return `${(n / 1_000).toFixed(1)} kbp`;
    return `${n} bp`;
  };

  return (
    <div className="genome-selector-page">
      <header className="genome-selector-header">
        <h1 className="logo">
          <span className="logo-gene">Gene</span>
          <span className="logo-life">Life</span>
        </h1>
        <p className="genome-selector-tagline">Select a genome to explore</p>
      </header>

      <div className="genome-card-grid">
        {genomes.map((g: GenomeSummary) => (
          <button
            key={g.genome_id}
            className="genome-card"
            onClick={() => selectGenome(g.genome_id)}
          >
            <div className="genome-card-accession">{g.accession}</div>
            <div className="genome-card-organism">{g.organism}</div>
            <div className="genome-card-stats">
              <span>{fmtBp(g.genome_length)}</span>
              <span>{g.total_genes} genes</span>
              {g.gc_content != null && <span>GC {g.gc_content.toFixed(1)}%</span>}
            </div>
            <div className="genome-card-badges">
              {g.is_circular && <span className="genome-badge circular">circular</span>}
              {g.genes_unknown > 0 && (
                <span className="genome-badge unknown">{g.genes_unknown} unknown</span>
              )}
            </div>
          </button>
        ))}

        <div className="genome-card genome-search-card">
          <div className="genome-search-header">Search NCBI</div>
          <input
            className="genome-search-input"
            type="text"
            placeholder="Search NCBI (e.g. mycoplasma)"
            value={searchQuery}
            onChange={(e) => handleSearch(e.target.value)}
          />
          {searching && <div className="genome-search-spinner">Searching...</div>}
          {error && <div className="genome-search-error">{error}</div>}
          {searchResults.length > 0 && (
            <div className="genome-search-results">
              {searchResults.map((r) => (
                <div key={r.accession} className="genome-search-row">
                  <div className="genome-search-row-info">
                    <div className="genome-search-row-organism">{r.organism}</div>
                    <div className="genome-search-row-meta">
                      <span>{r.accession}</span>
                      <span>{fmtBp(r.length)}</span>
                    </div>
                  </div>
                  <button
                    className="genome-search-import-btn"
                    disabled={importing !== null}
                    onClick={() => handleImport(r.accession)}
                  >
                    {importing === r.accession ? "Importing..." : "Import"}
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {genomes.length === 0 && !searchResults.length && (
        <div className="genome-selector-empty">
          <p>No genomes yet. Search NCBI to import your first genome.</p>
        </div>
      )}
    </div>
  );
}
