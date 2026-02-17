import { useGeneStore } from "../store";

export function GeneOverview() {
  const { geneRecord } = useGeneStore();
  if (!geneRecord) return null;

  const { identifiers: ids, summary, aliases, sequences } = geneRecord;

  return (
    <div className="panel gene-overview">
      <h2 className="panel-title">
        {ids.symbol}
        <span className="gene-name">{ids.name}</span>
      </h2>

      <div className="id-grid">
        {ids.ncbi_gene_id && <IdTag label="NCBI" value={ids.ncbi_gene_id} />}
        {ids.ensembl_gene && <IdTag label="Ensembl" value={ids.ensembl_gene} />}
        {ids.uniprot_id && <IdTag label="UniProt" value={ids.uniprot_id} />}
        {ids.refseq_mrna && <IdTag label="RefSeq" value={ids.refseq_mrna} />}
        {ids.chromosome && <IdTag label="Chr" value={ids.chromosome} />}
        {ids.map_location && <IdTag label="Locus" value={ids.map_location} />}
      </div>

      {aliases.length > 0 && (
        <p className="aliases">
          <strong>Aliases:</strong> {aliases.join(", ")}
        </p>
      )}

      {summary && <p className="summary">{summary}</p>}

      <div className="sequences-summary">
        <strong>Sequences loaded:</strong>{" "}
        {sequences.map((s) => (
          <span key={s.accession || s.seq_type} className="seq-tag">
            {s.seq_type} ({s.length.toLocaleString()} {s.seq_type === "protein" ? "aa" : "bp"})
          </span>
        ))}
      </div>
    </div>
  );
}

function IdTag({ label, value }: { label: string; value: string }) {
  return (
    <div className="id-tag">
      <span className="id-label">{label}</span>
      <span className="id-value">{value}</span>
    </div>
  );
}
