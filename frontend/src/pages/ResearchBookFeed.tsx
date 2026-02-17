import { useEffect } from "react";
import { Link } from "react-router-dom";
import { useResearchBookStore } from "../stores/researchBookStore";
import { ThreadCard } from "../components/researchbook/ThreadCard";
import { ThreadFilters } from "../components/researchbook/ThreadFilters";
import { SearchBar } from "../components/researchbook/SearchBar";

export function ResearchBookFeed() {
  const { feed, feedLoading, feedError, fetchFeed, filters, setFilters } =
    useResearchBookStore();

  useEffect(() => {
    fetchFeed();
  }, [fetchFeed]);

  return (
    <div style={{ maxWidth: 900, margin: "0 auto", padding: "2rem 1rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.5rem" }}>
        <h1 style={{ margin: 0 }}>ResearchBook</h1>
        <SearchBar />
      </div>

      <ThreadFilters filters={filters} onFilterChange={setFilters} />

      {feedLoading && <p>Loading feed...</p>}
      {feedError && <p style={{ color: "red" }}>{feedError}</p>}

      <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
        {feed.map((thread) => (
          <Link
            key={thread.thread_id}
            to={`/research/${thread.thread_id}`}
            style={{ textDecoration: "none", color: "inherit" }}
          >
            <ThreadCard thread={thread} />
          </Link>
        ))}
      </div>

      {!feedLoading && feed.length === 0 && (
        <p style={{ textAlign: "center", color: "#666", marginTop: "2rem" }}>
          No research threads yet. Run a dossier agent to create one.
        </p>
      )}
    </div>
  );
}
