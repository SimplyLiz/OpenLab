// ResearchBook types — mirrors backend schemas

export interface Claim {
  claim_text: string;
  confidence: number;
  citations: string[];
  citation_status: "valid" | "invalid" | "unchecked";
  is_speculative: boolean;
  section_title?: string;
}

export interface CommentRecord {
  comment_id: number;
  thread_id: number;
  author_name: string;
  body: string;
  comment_type: "comment" | "challenge" | "correction" | "endorsement";
  reply_to_comment_id?: number;
  referenced_claim_ids?: number[];
  challenge?: boolean;
  created_at: string;
}

export interface ForkRecord {
  fork_id: number;
  parent_thread_id: number;
  child_thread_id: number;
  modification_summary: string;
  modification_params?: Record<string, unknown>;
}

export interface ResearchThreadSummary {
  thread_id: number;
  title: string;
  summary?: string;
  gene_symbol: string;
  cancer_type?: string;
  status: "draft" | "published" | "challenged" | "superseded" | "archived";
  convergence_score?: number;
  confidence_tier?: number;
  comment_count: number;
  challenge_count: number;
  fork_count: number;
  created_at: string;
  updated_at: string;
}

export interface ResearchThreadDetail extends ResearchThreadSummary {
  agent_run_id?: string;
  claims_snapshot: Claim[];
  evidence_snapshot: Record<string, unknown>[];
  comments: CommentRecord[];
  forks: ForkRecord[];
  forked_from_id?: number;
}

export interface FeedResponse {
  threads: ResearchThreadSummary[];
  total: number;
  page: number;
  per_page: number;
}

export interface ThreadCreateRequest {
  agent_run_id: string;
  title?: string;
}

export interface CommentCreateRequest {
  author_name: string;
  body: string;
}

export interface ChallengeCreateRequest {
  author_name: string;
  body: string;
  claim_ids?: number[];
}

export interface ForkCreateRequest {
  cancer_type?: string;
  modification_summary: string;
  modification_params?: Record<string, unknown>;
}

export type FeedSortBy = "recent" | "convergence" | "challenges";

export interface FeedFilters {
  gene_symbol?: string;
  cancer_type?: string;
  status?: string;
  sort_by?: FeedSortBy;
  page?: number;
  per_page?: number;
}
