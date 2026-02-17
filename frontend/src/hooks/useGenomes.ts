import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useGeneStore } from "../store";
import type { GenomeSummary } from "../types";

const API = `${location.protocol}//${location.host}/api/v1`;

export function useGenomes() {
  const navigate = useNavigate();
  const genomes = useGeneStore((s) => s.genomes);
  const setGenomes = useGeneStore((s) => s.setGenomes);
  const setActiveGenomeId = useGeneStore((s) => s.setActiveGenomeId);

  const fetchGenomes = useCallback(async () => {
    try {
      const res = await fetch(`${API}/genomes`);
      if (!res.ok) return;
      const data: GenomeSummary[] = await res.json();
      setGenomes(data);
    } catch {
      // silent
    }
  }, [setGenomes]);

  const selectGenome = useCallback(
    (genomeId: number) => {
      setActiveGenomeId(genomeId);
      localStorage.setItem("biolab_last_genome", String(genomeId));
      navigate(`/g/${genomeId}`);
    },
    [setActiveGenomeId, navigate],
  );

  const searchNCBI = useCallback(async (query: string) => {
    const res = await fetch(`${API}/genomes/search?q=${encodeURIComponent(query)}`);
    if (!res.ok) throw new Error("Search failed");
    return res.json();
  }, []);

  const fetchGenome = useCallback(async (accession: string) => {
    const res = await fetch(`${API}/genomes/fetch`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ accession }),
    });
    if (!res.ok) throw new Error("Fetch failed");
    return res.json();
  }, []);

  return { genomes, fetchGenomes, selectGenome, searchNCBI, fetchGenome };
}

/**
 * Hook to load genome data when entering a genome-scoped page.
 * Hydrates from the API if the genome isn't already loaded.
 * Redirects to /genomes if the genome doesn't exist (404).
 */
export function useGenomeLoader(genomeId: string | undefined) {
  const { genome, activeGenomeId, setActiveGenomeId, handleEvent } = useGeneStore();
  const loadedRef = useRef<number | null>(null);
  const navigate = useNavigate();
  const [hydrateFailed, setHydrateFailed] = useState(false);

  useEffect(() => {
    if (!genomeId) return;
    const id = Number(genomeId);
    if (isNaN(id)) return;

    // Already loaded this genome
    if (genome && activeGenomeId === id && loadedRef.current === id) return;

    setActiveGenomeId(id);
    loadedRef.current = id;
    setHydrateFailed(false);

    // Hydrate from genome-specific endpoint
    (async () => {
      try {
        const res = await fetch(`${API}/genomes/${id}/hydrate`);
        if (res.ok) {
          const data = await res.json();
          handleEvent({
            stage: "genome_ingest",
            status: "completed",
            data,
            error: null,
            progress: 1.0,
          });
        } else {
          // Genome doesn't exist — clear stale bookmark and redirect
          localStorage.removeItem("biolab_last_genome");
          setHydrateFailed(true);
          navigate("/genomes", { replace: true });
        }
      } catch {
        setHydrateFailed(true);
      }
    })();
  }, [genomeId]); // eslint-disable-line react-hooks/exhaustive-deps

  return { hydrateFailed };
}
