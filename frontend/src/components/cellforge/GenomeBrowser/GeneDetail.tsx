interface GeneDetailProps {
  geneId: string;
  product: string;
  mrna: number;
  protein: number;
  isKO: boolean;
}

export function GeneDetail({ geneId, product, mrna, protein, isKO }: GeneDetailProps) {
  return (
    <div style={{
      marginTop: 4,
      padding: 6,
      background: '#1a1a2a',
      borderRadius: 4,
      fontSize: 11,
      color: '#ccc',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
        <b style={{ color: isKO ? '#f66' : '#fff' }}>{geneId}</b>
        {isKO && <span style={{ color: '#f66', fontSize: 10 }}>KNOCKED OUT</span>}
      </div>
      <div style={{ color: '#888' }}>{product}</div>
      <div style={{ display: 'flex', gap: 16, marginTop: 4 }}>
        <span>mRNA: <b style={{ color: '#4af' }}>{mrna}</b></span>
        <span>Protein: <b style={{ color: '#f84' }}>{protein}</b></span>
      </div>
    </div>
  );
}
