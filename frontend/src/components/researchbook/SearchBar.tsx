import { useState } from "react";
import { useNavigate } from "react-router-dom";

export function SearchBar() {
  const [query, setQuery] = useState("");
  const navigate = useNavigate();

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      navigate(`/research?search=${encodeURIComponent(query)}`);
    }
  };

  return (
    <form onSubmit={handleSearch} style={{ display: "flex", gap: "0.25rem" }}>
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search threads..."
        style={{
          padding: "6px 10px",
          border: "1px solid #ccc",
          borderRadius: 4,
          fontSize: "0.9rem",
          width: 200,
        }}
      />
      <button
        type="submit"
        style={{
          padding: "6px 12px",
          background: "#f0f0f0",
          border: "1px solid #ccc",
          borderRadius: 4,
          cursor: "pointer",
        }}
      >
        Search
      </button>
    </form>
  );
}
