# Changelog

All notable changes to **Local Knowledge Graph** are documented here.

## [1.0.0] - 2026-10-29

### Added
- Core Knowledge Vault: Markdown notes with wiki link `[[Note Title]]` extraction, automatic tag indexing, and bidirectional backlinks.
- Multi-format Document Ingestion Engine: SHA-256 content deduplication, automatic text normalization, overlapping chunking, and metadata extraction for TXT, MD, JSON, CSV, and HTML.
- SQLite FTS5 Full-Text Search: Porter tokenizer, Unicode61 normalization, BM25 rank scoring, and safe query sanitization.
- Local Dense Vector Semantic Search: 64-dimensional subword hash projection with cosine similarity calculation.
- Hybrid Search with Reciprocal Rank Fusion (RRF): Rank aggregation combining lexical FTS5 matches and semantic similarity.
- Persistent Knowledge Graph Engine: Entity extraction across Technology, Organization, Concept, and Project categories, degree centrality calculation, neighborhood expansion, and BFS shortest pathfinding.
- Interactive Graph Canvas: High-performance physics simulation layout with zoom/pan and accessible data table alternatives.
- Local Knowledge Assistant (RAG): Grounded context synthesis with verifiable source citations and evidence confidence detection.
- Data Portability & System Management: Full JSON export/import with conflict resolution and point-in-time SQLite backups.
