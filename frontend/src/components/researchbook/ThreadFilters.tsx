import type { FeedFilters, FeedSortBy } from "../../types/researchbook";

interface Props {
  filters: FeedFilters;
  onFilterChange: (filters: Partial<FeedFilters>) => void;
}

export function ThreadFilters({ filters, onFilterChange }: Props) {
  return (
    <div style={{ display: "flex", gap: "0.75rem", marginBottom: "1rem", flexWrap: "wrap" }}>
      <input
        type="text"
        placeholder="Gene symbol"
        value={filters.gene_symbol || ""}
        onChange={(e) => onFilterChange({ gene_symbol: e.target.value || undefined })}
        style={{ padding: "6px 8px", border: "1px solid #ccc", borderRadius: 4, width: 120 }}
      />

      <input
        type="text"
        placeholder="Cancer type"
        value={filters.cancer_type || ""}
        onChange={(e) => onFilterChange({ cancer_type: e.target.value || undefined })}
        style={{ padding: "6px 8px", border: "1px solid #ccc", borderRadius: 4, width: 120 }}
      />

      <select
        value={filters.status || ""}
        onChange={(e) => onFilterChange({ status: e.target.value || undefined })}
        style={{ padding: "6px 8px", border: "1px solid #ccc", borderRadius: 4 }}
      >
        <option value="">All statuses</option>
        <option value="published">Published</option>
        <option value="challenged">Challenged</option>
        <option value="draft">Draft</option>
      </select>

      <select
        value={filters.sort_by || "recent"}
        onChange={(e) => onFilterChange({ sort_by: e.target.value as FeedSortBy })}
        style={{ padding: "6px 8px", border: "1px solid #ccc", borderRadius: 4 }}
      >
        <option value="recent">Most Recent</option>
        <option value="convergence">Highest Convergence</option>
        <option value="challenges">Most Challenged</option>
      </select>
    </div>
  );
}
