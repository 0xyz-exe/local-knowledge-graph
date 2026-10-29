import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app.db.database import init_db, get_db
from backend.app.services.fts import update_fts_entry
from backend.app.services.ingestion import ingest_document

def seed():
    init_db()
    with get_db() as conn:
        cursor = conn.cursor()

        # Seed Notes
        notes = [
            (
                "note_01",
                "Graph Neural Networks & Relational Reasoning",
                "Graph Neural Networks (GNNs) operate on graph structured data. Message passing schemes propagate node features across [[Knowledge Graph]] edges. Integrates tightly with [[Python]] and [[FastAPI]] backend services.",
                "ai,gnn,graph",
                "research",
                1,
                0,
                "2026-10-28 10:00:00",
                "2026-10-28 10:00:00"
            ),
            (
                "note_02",
                "SQLite WAL Mode & Performance Optimization",
                "Write-Ahead Logging (WAL) in [[SQLite]] allows concurrent readers and a single writer without blocking. Use PRAGMA synchronous = NORMAL for optimal NVMe SSD durability and speed. Used by [[Local Knowledge Graph]] for local-first storage.",
                "database,performance,sqlite",
                "engineering",
                1,
                0,
                "2026-10-28 11:30:00",
                "2026-10-28 11:30:00"
            ),
            (
                "note_03",
                "Semantic Search with Reciprocal Rank Fusion",
                "Hybrid search combines lexical keyword matching from [[SQLite FTS5]] with dense vector embeddings using [[Reciprocal Rank Fusion]]. RRF Score formula: RRF(d) = sum(1 / (k + r(d))). Ensures high recall and precision.",
                "search,nlp,semantic",
                "architecture",
                0,
                0,
                "2026-10-28 14:15:00",
                "2026-10-28 14:15:00"
            ),
            (
                "note_04",
                "Local AI Privacy Architecture",
                "All user documents, notes, and embeddings remain strictly on the local machine. Zero mandatory external cloud dependencies. Supports optional local inference engines like [[Ollama]] or deterministic RAG pipelines.",
                "privacy,security,local-first",
                "security",
                0,
                0,
                "2026-10-28 16:45:00",
                "2026-10-28 16:45:00"
            )
        ]

        for n in notes:
            cursor.execute("SELECT id FROM notes WHERE id = ?", (n[0],))
            if not cursor.fetchone():
                cursor.execute("""
                INSERT INTO notes (id, title, content, tags, category, is_pinned, is_archived, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, n)
                update_fts_entry(conn, n[0], "note", n[1], n[2], n[3])

        # Seed Entities
        entities = [
            ("ent_fastapi", "FastAPI", "Technology", "Modern, fast asynchronous web framework for Python", "[]", 0.98, 1),
            ("ent_python", "Python", "Language", "High-level programming language powering the backend engine", "[]", 1.0, 1),
            ("ent_sqlite", "SQLite", "Database", "Embedded relational database engine with FTS5 and JSON support", "[]", 1.0, 1),
            ("ent_react", "React", "Technology", "Declarative UI library for building responsive interfaces", "[]", 0.95, 1),
            ("ent_kg", "Knowledge Graph", "Concept", "Interconnected network of real-world entities and relations", "[]", 0.95, 1),
            ("ent_rag", "Local RAG", "Concept", "Retrieval-Augmented Generation operating 100% offline", "[]", 0.92, 1),
            ("ent_rrf", "Reciprocal Rank Fusion", "Concept", "Transparent rank aggregation algorithm for hybrid search", "[]", 0.90, 1),
            ("ent_fts5", "SQLite FTS5", "Technology", "Full-text search engine extension for SQLite", "[]", 0.96, 1),
            ("ent_docker", "Docker", "Technology", "Containerization platform for isolated application deployments", "[]", 0.90, 1)
        ]

        for e in entities:
            cursor.execute("SELECT id FROM entities WHERE id = ?", (e[0],))
            if not cursor.fetchone():
                cursor.execute("""
                INSERT INTO entities (id, name, entity_type, description, aliases, confidence, is_user_created)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """, e)
                update_fts_entry(conn, e[0], "entity", e[1], e[3], e[2])

        # Seed Relationships
        relationships = [
            ("rel_01", "ent_fastapi", "ent_python", "WRITTEN_IN", 1.0, "curated", 1),
            ("rel_02", "ent_fastapi", "ent_sqlite", "PERSISTS_TO", 0.95, "curated", 1),
            ("rel_03", "ent_sqlite", "ent_fts5", "PROVIDES_EXTENSION", 1.0, "curated", 1),
            ("rel_04", "ent_kg", "ent_fastapi", "MANAGED_BY", 0.90, "curated", 1),
            ("rel_05", "ent_kg", "ent_react", "VISUALIZED_IN", 0.92, "curated", 1),
            ("rel_06", "ent_rag", "ent_rrf", "UTILIZES", 0.95, "curated", 1),
            ("rel_07", "ent_rrf", "ent_fts5", "AGGREGATES_FROM", 0.90, "curated", 1),
            ("rel_08", "ent_fastapi", "ent_docker", "CONTAINERIZED_BY", 0.85, "curated", 1)
        ]

        for r in relationships:
            cursor.execute("SELECT id FROM relationships WHERE id = ?", (r[0],))
            if not cursor.fetchone():
                cursor.execute("""
                INSERT OR IGNORE INTO relationships (id, source_id, target_id, relation_type, confidence, provenance, is_user_created)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """, r)

        # Seed Documents
        sample_doc_content = b"""# Local Knowledge Graph Architecture Specification
The Local Knowledge Graph platform combines SQLite FTS5 full-text search with local 64-dimensional dense vector embeddings.
All ingestion jobs extract named entities (Technologies, Concepts, Organizations) and generate bidirectional relationships.
Offline Local RAG synthesizes grounded answers with strict citation tracking and zero outbound network telemetry."""
        
        ingest_document(conn, "architecture_specification.md", sample_doc_content)

    print("Database successfully seeded with realistic demonstration knowledge!")

if __name__ == "__main__":
    seed()
