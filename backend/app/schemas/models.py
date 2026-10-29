from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

# Note models
class NoteCreate(BaseModel):
    title: str = Field(..., min_length=1)
    content: str
    tags: Optional[List[str]] = Field(default_factory=list)
    category: Optional[str] = "general"
    is_pinned: Optional[bool] = False

class NoteUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[List[str]] = None
    category: Optional[str] = None
    is_pinned: Optional[bool] = None
    is_archived: Optional[bool] = None

class NoteResponse(BaseModel):
    id: str
    title: str
    content: str
    tags: List[str]
    category: str
    is_pinned: bool
    is_archived: bool
    created_at: str
    updated_at: str
    outgoing_links: Optional[List[str]] = Field(default_factory=list)
    backlinks: Optional[List[Dict[str, Any]]] = Field(default_factory=list)

# Document models
class DocumentResponse(BaseModel):
    id: str
    filename: str
    file_type: str
    file_size: int
    content_hash: str
    extracted_text_preview: str
    chunk_count: int
    created_at: str
    updated_at: str

class DocumentDetailResponse(DocumentResponse):
    extracted_text: str
    chunks: List[Dict[str, Any]]

# Entity models
class EntityCreate(BaseModel):
    name: str = Field(..., min_length=1)
    entity_type: str = Field(..., min_length=1)
    description: Optional[str] = ""
    aliases: Optional[List[str]] = Field(default_factory=list)
    is_user_created: Optional[bool] = True

class EntityUpdate(BaseModel):
    name: Optional[str] = None
    entity_type: Optional[str] = None
    description: Optional[str] = None
    aliases: Optional[List[str]] = None

class EntityResponse(BaseModel):
    id: str
    name: str
    entity_type: str
    description: str
    aliases: List[str]
    confidence: float
    is_user_created: bool
    created_at: str
    updated_at: str
    mention_count: int = 0
    relationship_count: int = 0

class EntityMergeRequest(BaseModel):
    source_entity_id: str
    target_entity_id: str

# Relationship models
class RelationshipCreate(BaseModel):
    source_id: str
    target_id: str
    relation_type: str
    confidence: Optional[float] = 1.0
    provenance: Optional[str] = "manual"
    is_user_created: Optional[bool] = True

class RelationshipResponse(BaseModel):
    id: str
    source_id: str
    source_name: str
    source_type: str
    target_id: str
    target_name: str
    target_type: str
    relation_type: str
    confidence: float
    provenance: str
    is_user_created: bool
    created_at: str

# Graph Models
class GraphNode(BaseModel):
    id: str
    name: str
    label: str
    category: str
    node_type: str
    degree: int = 0

class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    relation: str
    confidence: float

class GraphOverviewResponse(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    stats: Dict[str, int]

# Search Models
class SearchQueryRequest(BaseModel):
    query: str
    mode: str = "hybrid"  # "fulltext", "semantic", "hybrid", "entity"
    filter_type: Optional[str] = None
    tag: Optional[str] = None
    limit: Optional[int] = 20

class SearchResultItem(BaseModel):
    item_id: str
    item_type: str  # 'note', 'document', 'entity'
    title: str
    snippet: str
    score: float
    match_type: str
    source_ref: Optional[str] = None
    tags: Optional[List[str]] = Field(default_factory=list)

class SearchResponse(BaseModel):
    query: str
    mode: str
    total_matches: int
    results: List[SearchResultItem]

# AI Assistant Models
class AIAskRequest(BaseModel):
    question: str
    max_context_chunks: Optional[int] = 5

class AICitation(BaseModel):
    source_id: str
    source_title: str
    source_type: str
    excerpt: str
    relevance_score: float

class AIAskResponse(BaseModel):
    question: str
    answer: str
    has_sufficient_evidence: bool
    citations: List[AICitation]
    graph_context: List[str]

# System Models
class DashboardStatsResponse(BaseModel):
    total_notes: int
    total_documents: int
    total_entities: int
    total_relationships: int
    total_chunks: int
    storage_size_bytes: int
    ai_status: Dict[str, Any]
    fts_status: Dict[str, Any]
