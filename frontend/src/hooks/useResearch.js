import { useCallback } from "react";
import { useGeneStore } from "../store";
const API = `${location.protocol}//${location.host}/api/v1/genes`;
export function useResearch() {
    const setResearchStatus = useGeneStore((s) => s.setResearchStatus);
    const fetchResearch = useCallback(async (locusTag) => {
        try {
            const res = await fetch(`${API}/locus/${locusTag}/research`);
            if (!res.ok)
                return null;
            const data = await res.json();
            setResearchStatus(locusTag, data);
            return data;
        }
        catch {
            return null;
        }
    }, [setResearchStatus]);
    const approveGene = useCallback(async (locusTag, proposedFunction) => {
        try {
            const res = await fetch(`${API}/locus/${locusTag}/approve`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ proposed_function: proposedFunction ?? null }),
            });
            if (res.ok) {
                await fetchResearch(locusTag);
                return true;
            }
            return false;
        }
        catch {
            return false;
        }
    }, [fetchResearch]);
    const rejectGene = useCallback(async (locusTag) => {
        try {
            const res = await fetch(`${API}/locus/${locusTag}/reject`, {
                method: "PATCH",
            });
            if (res.ok) {
                await fetchResearch(locusTag);
                return true;
            }
            return false;
        }
        catch {
            return false;
        }
    }, [fetchResearch]);
    const correctGene = useCallback(async (locusTag, correctedFunction) => {
        try {
            const res = await fetch(`${API}/locus/${locusTag}/correct`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ corrected_function: correctedFunction }),
            });
            if (res.ok) {
                await fetchResearch(locusTag);
                return true;
            }
            return false;
        }
        catch {
            return false;
        }
    }, [fetchResearch]);
    const fetchSummary = useCallback(async () => {
        try {
            const res = await fetch(`${API}/research/summary`);
            if (!res.ok)
                return null;
            return await res.json();
        }
        catch {
            return null;
        }
    }, []);
    return { fetchResearch, approveGene, rejectGene, correctGene, fetchSummary };
}
