import os
import uuid
import json
import sqlite3
import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status
from fastapi.responses import JSONResponse

from backend.app.db.database import get_db
from backend.app.schemas.models import (
    NoteCreate, NoteUpdate, NoteResponse,
    DocumentResponse, DocumentDetailResponse,
    EntityCreate, EntityUpdate, EntityResponse, EntityMergeRequest,
    RelationshipCreate, RelationshipResponse,
    GraphOverviewResponse,
    SearchQueryRequest, SearchResponse, SearchResultItem,
    AIAskRequest, AIAskResponse,
    DashboardStatsResponse
)
from backend.app.services.fts import search_fts, update_fts_entry, delete_fts_entry
from backend.app.services.semantic import (
    generate_local_embedding, cosine_similarity, reciprocal_rank_fusion
)
from backend.app.services.extractor import extract_wiki_links, extract_tags, extract_entities_from_text
from backend.app.services.graph import get_graph_overview, get_node_neighbors, find_shortest_path
from backend.app.services.ingestion import ingest_document
from backend.app.services.assistant import query_knowledge_assistant
from backend.app.services.export_import import export_knowledge_json, import_knowledge_json, create_db_backup
from backend.app.core.config import DB_PATH, UPLOADS_DIR, MAX_UPLOAD_SIZE_BYTES

router = APIRouter(prefix="/v1")

# ==========================================
# 1. DASHBOARD & SYSTEM
# ==========================================

@router.get("/dashboard/stats", response_model=DashboardStatsResponse)
def get_dashboard_stats():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM notes WHERE is_archived = 0")
        total_notes = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM documents")
        total_docs = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM entities")
        total_entities = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM relationships")
        total_relationships = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM document_chunks")
        total_chunks = cursor.fetchone()[0]

        storage_size = 0
        if DB_PATH.exists():
            storage_size += DB_PATH.stat().st_size
        if UPLOADS_DIR.exists():
            storage_size += sum(f.stat().st_size for f in UPLOADS_DIR.glob("*") if f.is_file())

        return DashboardStatsResponse(
            total_notes=total_notes,
            total_documents=total_docs,
            total_entities=total_entities,
            total_relationships=total_relationships,
            total_chunks=total_chunks,
            storage_size_bytes=storage_size,
            ai_status={
                "mode": "offline-local",
                "embedding_model": "deterministic-hash-projection-64d",
                "status": "ready",
                "local_ai_available": True
            },
            fts_status={
                "engine": "sqlite-fts5",
                "tokenizer": "porter unicode61",
                "status": "active"
            }
        )

# ==========================================
# 2. NOTES MANAGEMENT
# ==========================================

@router.get("/notes", response_model=List[NoteResponse])
def list_notes(
    tag: Optional[str] = None,
    category: Optional[str] = None,
    include_archived: bool = False
):
    with get_db() as conn:
        cursor = conn.cursor()
        sql = "SELECT id, title, content, tags, category, is_pinned, is_archived, created_at, updated_at FROM notes WHERE 1=1"
        params: List[Any] = []

        if not include_archived:
            sql += " AND is_archived = 0"
        if category:
            sql += " AND category = ?"
            params.append(category)
        if tag:
            sql += " AND tags LIKE ?"
            params.append(f"%{tag}%")

        sql += " ORDER BY is_pinned DESC, updated_at DESC"
        cursor.execute(sql, params)
        rows = cursor.fetchall()

        result = []
        for r in rows:
            tags_list = [t.strip() for t in r["tags"].split(",") if t.strip()] if r["tags"] else []
            links = extract_wiki_links(r["content"])
            result.append(NoteResponse(
                id=r["id"],
                title=r["title"],
                content=r["content"],
                tags=tags_list,
                category=r["category"],
                is_pinned=bool(r["is_pinned"]),
                is_archived=bool(r["is_archived"]),
                created_at=r["created_at"],
                updated_at=r["updated_at"],
                outgoing_links=links,
                backlinks=[]
            ))
        return result

@router.post("/notes", response_model=NoteResponse)
def create_note(payload: NoteCreate):
    with get_db() as conn:
        cursor = conn.cursor()
        note_id = f"note_{uuid.uuid4().hex[:10]}"
        now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        # Automatically extract tags and links
        extracted_tags = extract_tags(payload.content)
        combined_tags = list(set((payload.tags or []) + extracted_tags))
        tags_str = ",".join(combined_tags)

        cursor.execute("""
        INSERT INTO notes (id, title, content, tags, category, is_pinned, is_archived, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?)
        """, (note_id, payload.title, payload.content, tags_str, payload.category or "general", 1 if payload.is_pinned else 0, now, now))

        # Index in FTS
        update_fts_entry(conn, note_id, "note", payload.title, payload.content, tags_str)

        # Extract entities from note content
        entities = extract_entities_from_text(payload.content)
        for ent in entities:
            cursor.execute("SELECT id FROM entities WHERE name = ? COLLATE NOCASE", (ent["name"],))
            existing = cursor.fetchone()
            if existing:
                eid = existing["id"]
            else:
                eid = f"ent_{uuid.uuid4().hex[:10]}"
                cursor.execute("""
                INSERT INTO entities (id, name, entity_type, description, confidence, is_user_created)
                VALUES (?, ?, ?, ?, ?, 0)
                """, (eid, ent["name"], ent["entity_type"], ent["description"], ent["confidence"]))
            
            # Record mention
            mid = f"men_{uuid.uuid4().hex[:10]}"
            cursor.execute("""
            INSERT INTO entity_mentions (id, entity_id, source_type, source_id, snippet, confidence)
            VALUES (?, ?, 'note', ?, ?, ?)
            """, (mid, eid, note_id, payload.title, ent["confidence"]))

        outgoing = extract_wiki_links(payload.content)

        return NoteResponse(
            id=note_id,
            title=payload.title,
            content=payload.content,
            tags=combined_tags,
            category=payload.category or "general",
            is_pinned=bool(payload.is_pinned),
            is_archived=False,
            created_at=now,
            updated_at=now,
            outgoing_links=outgoing,
            backlinks=[]
        )

@router.get("/notes/{id}", response_model=NoteResponse)
def get_note(id: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM notes WHERE id = ?", (id,))
        r = cursor.fetchone()
        if not r:
            raise HTTPException(status_code=404, detail="Note not found")

        tags_list = [t.strip() for t in r["tags"].split(",") if t.strip()] if r["tags"] else []
        outgoing = extract_wiki_links(r["content"])

        # Find backlinks: other notes mentioning this note title
        cursor.execute("SELECT id, title FROM notes WHERE id != ? AND content LIKE ?", (id, f"%[[{r['title']}]]%"))
        backlinks = [{"id": b["id"], "title": b["title"]} for b in cursor.fetchall()]

        return NoteResponse(
            id=r["id"],
            title=r["title"],
            content=r["content"],
            tags=tags_list,
            category=r["category"],
            is_pinned=bool(r["is_pinned"]),
            is_archived=bool(r["is_archived"]),
            created_at=r["created_at"],
            updated_at=r["updated_at"],
            outgoing_links=outgoing,
            backlinks=backlinks
        )

@router.put("/notes/{id}", response_model=NoteResponse)
def update_note(id: str, payload: NoteUpdate):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM notes WHERE id = ?", (id,))
        r = cursor.fetchone()
        if not r:
            raise HTTPException(status_code=404, detail="Note not found")

        now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        new_title = payload.title if payload.title is not None else r["title"]
        new_content = payload.content if payload.content is not None else r["content"]
        new_cat = payload.category if payload.category is not None else r["category"]
        new_pinned = 1 if (payload.is_pinned if payload.is_pinned is not None else r["is_pinned"]) else 0
        new_archived = 1 if (payload.is_archived if payload.is_archived is not None else r["is_archived"]) else 0

        if payload.tags is not None:
            new_tags_list = payload.tags
        else:
            new_tags_list = [t.strip() for t in r["tags"].split(",") if t.strip()] if r["tags"] else []

        new_tags_str = ",".join(new_tags_list)

        cursor.execute("""
        UPDATE notes
        SET title = ?, content = ?, tags = ?, category = ?, is_pinned = ?, is_archived = ?, updated_at = ?
        WHERE id = ?
        """, (new_title, new_content, new_tags_str, new_cat, new_pinned, new_archived, now, id))

        update_fts_entry(conn, id, "note", new_title, new_content, new_tags_str)

        outgoing = extract_wiki_links(new_content)
        return NoteResponse(
            id=id,
            title=new_title,
            content=new_content,
            tags=new_tags_list,
            category=new_cat,
            is_pinned=bool(new_pinned),
            is_archived=bool(new_archived),
            created_at=r["created_at"],
            updated_at=now,
            outgoing_links=outgoing,
            backlinks=[]
        )

@router.delete("/notes/{id}")
def delete_note(id: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM notes WHERE id = ?", (id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Note not found")
        delete_fts_entry(conn, id, "note")
        cursor.execute("DELETE FROM entity_mentions WHERE source_id = ? AND source_type = 'note'", (id,))
        return {"status": "deleted", "id": id}

# ==========================================
# 3. DOCUMENTS & INGESTION
# ==========================================

@router.get("/documents", response_model=List[DocumentResponse])
def list_documents():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT id, filename, file_type, file_size, content_hash, extracted_text, chunk_count, created_at, updated_at 
        FROM documents 
        ORDER BY created_at DESC
        """)
        rows = cursor.fetchall()
        result = []
        for r in rows:
            preview = (r["extracted_text"][:240] + "...") if len(r["extracted_text"]) > 240 else r["extracted_text"]
            result.append(DocumentResponse(
                id=r["id"],
                filename=r["filename"],
                file_type=r["file_type"],
                file_size=r["file_size"],
                content_hash=r["content_hash"],
                extracted_text_preview=preview,
                chunk_count=r["chunk_count"],
                created_at=r["created_at"],
                updated_at=r["updated_at"]
            ))
        return result

@router.get("/documents/{id}", response_model=DocumentDetailResponse)
def get_document(id: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM documents WHERE id = ?", (id,))
        r = cursor.fetchone()
        if not r:
            raise HTTPException(status_code=404, detail="Document not found")

        cursor.execute("SELECT id, chunk_index, text, token_count FROM document_chunks WHERE document_id = ? ORDER BY chunk_index ASC", (id,))
        chunks = [dict(c) for c in cursor.fetchall()]

        preview = (r["extracted_text"][:240] + "...") if len(r["extracted_text"]) > 240 else r["extracted_text"]
        return DocumentDetailResponse(
            id=r["id"],
            filename=r["filename"],
            file_type=r["file_type"],
            file_size=r["file_size"],
            content_hash=r["content_hash"],
            extracted_text_preview=preview,
            chunk_count=r["chunk_count"],
            created_at=r["created_at"],
            updated_at=r["updated_at"],
            extracted_text=r["extracted_text"],
            chunks=chunks
        )

@router.post("/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    content_bytes = await file.read()
    if len(content_bytes) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(status_code=413, detail=f"File exceeds maximum allowed limit of {MAX_UPLOAD_SIZE_BYTES // (1024*1024)}MB")

    with get_db() as conn:
        fname = file.filename or "uploaded_file.txt"
        result = ingest_document(conn, fname, content_bytes)
        return result

@router.delete("/documents/{id}")
def delete_document(id: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT file_path FROM documents WHERE id = ?", (id,))
        r = cursor.fetchone()
        if not r:
            raise HTTPException(status_code=404, detail="Document not found")

        # Delete from disk safely
        fpath = Path(r["file_path"])
        if fpath.exists():
            try:
                fpath.unlink()
            except Exception:
                pass

        cursor.execute("DELETE FROM documents WHERE id = ?", (id,))
        delete_fts_entry(conn, id, "document")
        cursor.execute("DELETE FROM entity_mentions WHERE source_id = ? AND source_type = 'document'", (id,))
        return {"status": "deleted", "id": id}

# ==========================================
# 4. SEARCH (FULL-TEXT, SEMANTIC, HYBRID)
# ==========================================

@router.post("/search/query", response_model=SearchResponse)
def execute_search(payload: SearchQueryRequest):
    with get_db() as conn:
        q = payload.query.strip()
        if not q:
            return SearchResponse(query=payload.query, mode=payload.mode, total_matches=0, results=[])

        fts_matches = []
        if payload.mode in ["fulltext", "hybrid", "all"]:
            fts_matches = search_fts(conn, q, filter_type=payload.filter_type, limit=payload.limit or 20)

        semantic_matches = []
        if payload.mode in ["semantic", "hybrid", "all"]:
            q_vec = generate_local_embedding(q)
            cursor = conn.cursor()
            cursor.execute("""
            SELECT c.id, c.document_id, c.text, c.vector_json, d.filename 
            FROM document_chunks c
            JOIN documents d ON c.document_id = d.id
            """)
            chunks = cursor.fetchall()

            for c in chunks:
                try:
                    vec = json.loads(c["vector_json"])
                    sim = cosine_similarity(q_vec, vec)
                    if sim > 0.05:
                        semantic_matches.append({
                            "item_id": c["document_id"],
                            "item_type": "document",
                            "title": c["filename"],
                            "snippet": c["text"][:280] + ("..." if len(c["text"]) > 280 else ""),
                            "score": round(sim, 4),
                            "match_type": "semantic"
                        })
                except Exception:
                    continue

            semantic_matches.sort(key=lambda x: x["score"], reverse=True)
            semantic_matches = semantic_matches[:(payload.limit or 20)]

        # Determine final ranked results
        if payload.mode == "fulltext":
            final_items = fts_matches
        elif payload.mode == "semantic":
            final_items = semantic_matches
        else: # "hybrid" or "all"
            final_items = reciprocal_rank_fusion(fts_matches, semantic_matches)

        response_items = [
            SearchResultItem(
                item_id=item["item_id"],
                item_type=item["item_type"],
                title=item["title"],
                snippet=item["snippet"],
                score=float(item["score"]),
                match_type=item.get("match_type", "hybrid")
            )
            for item in final_items[:payload.limit or 20]
        ]

        return SearchResponse(
            query=payload.query,
            mode=payload.mode,
            total_matches=len(response_items),
            results=response_items
        )

# ==========================================
# 5. ENTITIES & RELATIONSHIPS
# ==========================================

@router.get("/entities", response_model=List[EntityResponse])
def list_entities(entity_type: Optional[str] = None):
    with get_db() as conn:
        cursor = conn.cursor()
        sql = "SELECT * FROM entities"
        params = []
        if entity_type:
            sql += " WHERE entity_type = ?"
            params.append(entity_type)
        sql += " ORDER BY name ASC"
        cursor.execute(sql, params)
        rows = cursor.fetchall()

        result = []
        for r in rows:
            cursor.execute("SELECT COUNT(*) FROM entity_mentions WHERE entity_id = ?", (r["id"],))
            m_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM relationships WHERE source_id = ? OR target_id = ?", (r["id"], r["id"]))
            r_count = cursor.fetchone()[0]

            result.append(EntityResponse(
                id=r["id"],
                name=r["name"],
                entity_type=r["entity_type"],
                description=r["description"] or "",
                aliases=json.loads(r["aliases"] or "[]"),
                confidence=float(r["confidence"]),
                is_user_created=bool(r["is_user_created"]),
                created_at=r["created_at"],
                updated_at=r["updated_at"],
                mention_count=m_count,
                relationship_count=r_count
            ))
        return result

@router.post("/entities", response_model=EntityResponse)
def create_entity(payload: EntityCreate):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM entities WHERE name = ? COLLATE NOCASE", (payload.name,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Entity with this name already exists")

        eid = f"ent_{uuid.uuid4().hex[:10]}"
        now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        aliases_json = json.dumps(payload.aliases or [])

        cursor.execute("""
        INSERT INTO entities (id, name, entity_type, description, aliases, confidence, is_user_created, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, 1.0, 1, ?, ?)
        """, (eid, payload.name, payload.entity_type, payload.description or "", aliases_json, now, now))

        update_fts_entry(conn, eid, "entity", payload.name, payload.description or "", payload.entity_type)

        return EntityResponse(
            id=eid,
            name=payload.name,
            entity_type=payload.entity_type,
            description=payload.description or "",
            aliases=payload.aliases or [],
            confidence=1.0,
            is_user_created=True,
            created_at=now,
            updated_at=now,
            mention_count=0,
            relationship_count=0
        )

@router.post("/entities/merge")
def merge_entities(payload: EntityMergeRequest):
    """Safely merge source entity into target entity, updating mentions and relationships."""
    with get_db() as conn:
        cursor = conn.cursor()
        if payload.source_entity_id == payload.target_entity_id:
            raise HTTPException(status_code=400, detail="Cannot merge entity into itself")

        cursor.execute("SELECT id, name FROM entities WHERE id = ?", (payload.source_entity_id,))
        src = cursor.fetchone()
        cursor.execute("SELECT id, name, aliases FROM entities WHERE id = ?", (payload.target_entity_id,))
        tgt = cursor.fetchone()

        if not src or not tgt:
            raise HTTPException(status_code=404, detail="Source or target entity not found")

        # Update target aliases
        tgt_aliases = json.loads(tgt["aliases"] or "[]")
        if src["name"] not in tgt_aliases:
            tgt_aliases.append(src["name"])
        cursor.execute("UPDATE entities SET aliases = ? WHERE id = ?", (json.dumps(tgt_aliases), tgt["id"]))

        # Move mentions
        cursor.execute("UPDATE entity_mentions SET entity_id = ? WHERE entity_id = ?", (tgt["id"], src["id"]))

        # Update relationships
        cursor.execute("UPDATE OR IGNORE relationships SET source_id = ? WHERE source_id = ?", (tgt["id"], src["id"]))
        cursor.execute("UPDATE OR IGNORE relationships SET target_id = ? WHERE target_id = ?", (tgt["id"], src["id"]))

        # Remove source entity
        cursor.execute("DELETE FROM entities WHERE id = ?", (src["id"],))
        delete_fts_entry(conn, src["id"], "entity")

        return {
            "status": "merged",
            "source_id": src["id"],
            "target_id": tgt["id"],
            "message": f"Successfully merged '{src['name']}' into '{tgt['name']}'."
        }

@router.delete("/entities/{id}")
def delete_entity(id: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM entities WHERE id = ?", (id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Entity not found")
        delete_fts_entry(conn, id, "entity")
        return {"status": "deleted", "id": id}

# ==========================================
# 6. KNOWLEDGE GRAPH
# ==========================================

@router.get("/graph/overview", response_model=GraphOverviewResponse)
def get_graph():
    with get_db() as conn:
        data = get_graph_overview(conn)
        return GraphOverviewResponse(
            nodes=data["nodes"],
            edges=data["edges"],
            stats=data["stats"]
        )

@router.get("/graph/node/{id}/neighbors")
def get_neighbors(id: str, depth: int = Query(default=1, ge=1, le=3)):
    with get_db() as conn:
        return get_node_neighbors(conn, id, depth=depth)

@router.get("/graph/paths")
def get_paths(source_id: str, target_id: str):
    with get_db() as conn:
        path = find_shortest_path(conn, source_id, target_id)
        return {"source_id": source_id, "target_id": target_id, "path": path}

@router.post("/graph/relationships", response_model=RelationshipResponse)
def create_relationship(payload: RelationshipCreate):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, entity_type FROM entities WHERE id = ?", (payload.source_id,))
        src = cursor.fetchone()
        cursor.execute("SELECT id, name, entity_type FROM entities WHERE id = ?", (payload.target_id,))
        tgt = cursor.fetchone()

        if not src or not tgt:
            raise HTTPException(status_code=404, detail="Source or target entity not found")

        rel_id = f"rel_{uuid.uuid4().hex[:10]}"
        now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        try:
            cursor.execute("""
            INSERT INTO relationships (id, source_id, target_id, relation_type, confidence, provenance, is_user_created, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 1, ?)
            """, (rel_id, payload.source_id, payload.target_id, payload.relation_type, payload.confidence or 1.0, payload.provenance or "manual", now))
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=400, detail="This relationship already exists")

        return RelationshipResponse(
            id=rel_id,
            source_id=src["id"],
            source_name=src["name"],
            source_type=src["entity_type"],
            target_id=tgt["id"],
            target_name=tgt["name"],
            target_type=tgt["entity_type"],
            relation_type=payload.relation_type,
            confidence=payload.confidence or 1.0,
            provenance=payload.provenance or "manual",
            is_user_created=True,
            created_at=now
        )

@router.delete("/graph/relationships/{id}")
def delete_relationship(id: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM relationships WHERE id = ?", (id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Relationship not found")
        return {"status": "deleted", "id": id}

# ==========================================
# 7. AI ASSISTANT
# ==========================================

@router.post("/ai/query", response_model=AIAskResponse)
def ask_assistant(payload: AIAskRequest):
    with get_db() as conn:
        return query_knowledge_assistant(
            conn=conn,
            question=payload.question,
            max_context_chunks=payload.max_context_chunks or 5
        )

@router.get("/ai/status")
def ai_status():
    return {
        "status": "ready",
        "provider": "local-deterministic-rag",
        "offline": True,
        "paid_api_required": False
    }

# ==========================================
# 8. EXPORT, IMPORT & SYSTEM
# ==========================================

@router.get("/system/export")
def export_system():
    with get_db() as conn:
        return export_knowledge_json(conn)

@router.post("/system/import")
def import_system(payload: Dict[str, Any]):
    with get_db() as conn:
        return import_knowledge_json(conn, payload)

@router.post("/system/backup")
def backup_system():
    path = create_db_backup()
    return {"status": "backup_created", "backup_path": path}

@router.post("/system/reindex")
def reindex_system():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM fts_index")

        # Re-index all notes
        cursor.execute("SELECT id, title, content, tags FROM notes WHERE is_archived = 0")
        for n in cursor.fetchall():
            update_fts_entry(conn, n["id"], "note", n["title"], n["content"], n["tags"])

        # Re-index all documents
        cursor.execute("SELECT id, filename, extracted_text, file_type FROM documents")
        for d in cursor.fetchall():
            update_fts_entry(conn, d["id"], "document", d["filename"], d["extracted_text"], d["file_type"])

        # Re-index all entities
        cursor.execute("SELECT id, name, description, entity_type FROM entities")
        for e in cursor.fetchall():
            update_fts_entry(conn, e["id"], "entity", e["name"], e["description"] or "", e["entity_type"])

        return {"status": "reindexed"}
