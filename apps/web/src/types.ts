export interface Note {
  id: string;
  title: string;
  content: string;
  tags: string[];
  category: string;
  is_pinned: boolean;
  is_archived: boolean;
  created_at: string;
  updated_at: string;
  outgoing_links: string[];
  backlinks: { id: string; title: string }[];
}

export interface DocumentItem {
  id: string;
  filename: string;
  file_type: string;
  file_size: number;
  content_hash: string;
  extracted_text_preview: string;
  chunk_count: number;
  created_at: string;
  updated_at: string;
}

export interface DocumentDetail extends DocumentItem {
  extracted_text: string;
  chunks: { id: string; chunk_index: number; text: string; token_count: number }[];
}

export interface Entity {
  id: string;
  name: string;
  entity_type: string;
  description: string;
  aliases: string[];
  confidence: number;
  is_user_created: boolean;
  created_at: string;
  updated_at: string;
  mention_count: number;
  relationship_count: number;
}

export interface Relationship {
  id: string;
  source_id: string;
  source_name: string;
  source_type: string;
  target_id: string;
  target_name: string;
  target_type: string;
  relation_type: string;
  confidence: number;
  provenance: string;
  is_user_created: boolean;
  created_at: string;
}

export interface GraphNode {
  id: string;
  name: string;
  label: string;
  category: string;
  node_type: string;
  degree: number;
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  relation: string;
  confidence: number;
}

export interface GraphOverview {
  nodes: GraphNode[];
  edges: GraphEdge[];
  stats: {
    node_count: number;
    edge_count: number;
    total_entities: number;
    total_relationships: number;
  };
}

export interface SearchResultItem {
  item_id: string;
  item_type: 'note' | 'document' | 'entity';
  title: string;
  snippet: string;
  score: number;
  match_type: 'fulltext' | 'semantic' | 'hybrid';
}

export interface AICitation {
  source_id: string;
  source_title: string;
  source_type: string;
  excerpt: string;
  relevance_score: number;
}

export interface AIAskResponse {
  question: string;
  answer: string;
  has_sufficient_evidence: boolean;
  citations: AICitation[];
  graph_context: string[];
}

export interface DashboardStats {
  total_notes: number;
  total_documents: number;
  total_entities: number;
  total_relationships: number;
  total_chunks: number;
  storage_size_bytes: number;
  ai_status: {
    mode: string;
    embedding_model: string;
    status: string;
    local_ai_available: boolean;
  };
  fts_status: {
    engine: string;
    tokenizer: string;
    status: string;
  };
}
