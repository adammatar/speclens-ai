export const DEFAULT_WORKSPACE_ID = "00000000-0000-4000-8000-000000000001";

export type DocumentSummary = {
  id: string;
  workspace_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  version_count: number;
  latest_status: string | null;
};

export type DocumentVersion = {
  id: string;
  version_number: number;
  filename: string;
  content_type: string;
  byte_size: number;
  sha256: string;
  status: string;
  error_message: string | null;
  page_count: number | null;
  created_at: string;
  chunk_count: number;
};

export type DocumentDetail = {
  id: string;
  workspace_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  versions: DocumentVersion[];
};

export type Chunk = {
  id: string;
  chunk_index: number;
  text: string;
  heading_path: string;
  page_number: number | null;
  start_offset: number;
  end_offset: number;
  token_count: number;
};

export type JobStatus = {
  id: string;
  document_version_id: string;
  status: string;
  progress_pct: number;
  error_message: string | null;
  attempts: number;
};

export type ConversationSummary = {
  id: string;
  workspace_id: string;
  title: string;
  created_at: string;
  updated_at: string;
};

export type AnswerTurn = {
  conversation_id: string;
  user_message_id: string;
  assistant_message_id: string;
  status: string;
  content: string;
  retrieval_status: string;
  generation_status: string;
  retrieved_chunk_ids: string[];
  citation_chunk_ids: string[];
  model?: string | null;
  generation_backend?: string | null;
};

export type Requirement = {
  id: string;
  workspace_id: string;
  document_id: string;
  document_version_id: string;
  statement: string;
  requirement_type: string;
  priority: string;
  review_state: string;
  confidence: number;
  sources: Array<Record<string, unknown>>;
};

export type RequirementChange = {
  id: string;
  category: string;
  decision: string;
  old_statement: string | null;
  new_statement: string | null;
  old_source_quote: string | null;
  new_source_quote: string | null;
  is_eval_example: boolean;
};

export type ComparisonJob = {
  id: string;
  status: string;
  progress_pct: number;
  change_count: number;
  base_document_version_id: string;
  target_document_version_id: string;
  changes: RequirementChange[];
};

export type MetaInfo = {
  version: string;
  deployment_mode: string;
  retention_days: number;
  auth_required: boolean;
  embedding_backend: string;
  generation_backend: string;
  extraction_backend: string;
};
