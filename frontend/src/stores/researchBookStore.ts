import { create } from "zustand";
import type {
  ResearchThreadSummary,
  ResearchThreadDetail,
  FeedFilters,
} from "../types/researchbook";

const API_BASE = "/api/v1/researchbook";

interface ResearchBookState {
  // Feed state
  feed: ResearchThreadSummary[];
  feedLoading: boolean;
  feedError: string | null;
  feedTotal: number;
  filters: FeedFilters;

  // Active thread
  activeThread: ResearchThreadDetail | null;
  threadLoading: boolean;

  // Actions
  fetchFeed: (filters?: FeedFilters) => Promise<void>;
  fetchThread: (threadId: number) => Promise<void>;
  createThread: (agentRunId: string, title?: string) => Promise<number>;
  publishThread: (threadId: number) => Promise<void>;
  addComment: (threadId: number, authorName: string, body: string) => Promise<void>;
  challengeThread: (threadId: number, authorName: string, body: string) => Promise<void>;
  forkThread: (threadId: number, cancerType: string, summary: string) => Promise<number>;
  searchThreads: (query: string) => Promise<ResearchThreadSummary[]>;
  setFilters: (filters: Partial<FeedFilters>) => void;
}

export const useResearchBookStore = create<ResearchBookState>((set, get) => ({
  feed: [],
  feedLoading: false,
  feedError: null,
  feedTotal: 0,
  filters: { page: 1, per_page: 20, sort_by: "recent" },
  activeThread: null,
  threadLoading: false,

  setFilters: (filters) => {
    set((s) => ({ filters: { ...s.filters, ...filters } }));
    get().fetchFeed();
  },

  fetchFeed: async (filters) => {
    const f = filters || get().filters;
    set({ feedLoading: true, feedError: null });
    try {
      const params = new URLSearchParams();
      if (f.gene_symbol) params.set("gene_symbol", f.gene_symbol);
      if (f.cancer_type) params.set("cancer_type", f.cancer_type);
      if (f.status) params.set("status", f.status);
      if (f.sort_by) params.set("sort_by", f.sort_by);
      if (f.page) params.set("page", String(f.page));
      if (f.per_page) params.set("per_page", String(f.per_page));

      const resp = await fetch(`${API_BASE}/feed?${params}`);
      const data = await resp.json();
      set({ feed: data, feedTotal: data.length, feedLoading: false });
    } catch (e) {
      set({ feedError: String(e), feedLoading: false });
    }
  },

  fetchThread: async (threadId) => {
    set({ threadLoading: true });
    try {
      const resp = await fetch(`${API_BASE}/threads/${threadId}`);
      const data = await resp.json();
      set({ activeThread: data, threadLoading: false });
    } catch {
      set({ threadLoading: false });
    }
  },

  createThread: async (agentRunId, title) => {
    const resp = await fetch(`${API_BASE}/threads`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ agent_run_id: agentRunId, title }),
    });
    const data = await resp.json();
    return data.thread_id;
  },

  publishThread: async (threadId) => {
    await fetch(`${API_BASE}/threads/${threadId}/publish`, { method: "PATCH" });
    get().fetchThread(threadId);
  },

  addComment: async (threadId, authorName, body) => {
    await fetch(`${API_BASE}/threads/${threadId}/comments`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ author_name: authorName, body }),
    });
    get().fetchThread(threadId);
  },

  challengeThread: async (threadId, authorName, body) => {
    await fetch(`${API_BASE}/threads/${threadId}/challenge`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ author_name: authorName, body }),
    });
    get().fetchThread(threadId);
  },

  forkThread: async (threadId, cancerType, summary) => {
    const resp = await fetch(`${API_BASE}/threads/${threadId}/fork`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        cancer_type: cancerType,
        modification_summary: summary,
      }),
    });
    const data = await resp.json();
    return data.child_thread_id;
  },

  searchThreads: async (query) => {
    const resp = await fetch(`${API_BASE}/search?query=${encodeURIComponent(query)}`);
    return resp.json();
  },
}));
