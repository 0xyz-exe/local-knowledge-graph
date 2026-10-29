import os
import tempfile
import pytest
from fastapi.testclient import TestClient

from backend.app.core.config import DB_PATH
from backend.app.db.database import init_db, get_db
from backend.app.main import app
from backend.app.services.fts import update_fts_entry, search_fts
from backend.app.services.semantic import generate_local_embedding, cosine_similarity, reciprocal_rank_fusion
from backend.app.services.extractor import extract_wiki_links, extract_tags, extract_entities_from_text
from backend.app.services.graph import get_graph_overview, get_node_neighbors, find_shortest_path
from backend.app.services.ingestion import chunk_text, ingest_document
from backend.app.services.assistant import query_knowledge_assistant
from backend.app.services.export_import import export_knowledge_json, import_knowledge_json

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_test_db(tmp_path, monkeypatch):
    test_db = tmp_path / "test_kg.sqlite3"
    monkeypatch.setattr("backend.app.core.config.DB_PATH", test_db)
    monkeypatch.setattr("backend.app.db.database.DB_PATH", test_db)
    monkeypatch.setattr("backend.app.api.v1.endpoints.DB_PATH", test_db)
    init_db(str(test_db))
    yield str(test_db)

def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"

def test_dashboard_stats_empty():
    res = client.get("/api/v1/dashboard/stats")
    assert res.status_code == 200
    data = res.json()
    assert data["total_notes"] == 0
    assert data["total_documents"] == 0
    assert data["total_entities"] == 0

def test_notes_crud_and_links():
    # 1. Create note
    payload = {
        "title": "Architecture Overview",
        "content": "Designing a #system using [[FastAPI]] and [[React]]. Also mentions Python.",
        "category": "design",
        "is_pinned": True
    }
    res = client.post("/api/v1/notes", json=payload)
    assert res.status_code == 200
    note = res.json()
    assert note["title"] == "Architecture Overview"
    assert "FastAPI" in note["outgoing_links"]
    assert "system" in note["tags"]
    note_id = note["id"]

    # 2. Get note
    res = client.get(f"/api/v1/notes/{note_id}")
    assert res.status_code == 200
    assert res.json()["is_pinned"] is True

    # 3. Update note
    update_payload = {"title": "Updated Architecture Overview", "is_pinned": False}
    res = client.put(f"/api/v1/notes/{note_id}", json=update_payload)
    assert res.status_code == 200
    assert res.json()["title"] == "Updated Architecture Overview"
    assert res.json()["is_pinned"] is False

    # 4. List notes
    res = client.get("/api/v1/notes")
    assert len(res.json()) == 1

    # 5. Delete note
    res = client.delete(f"/api/v1/notes/{note_id}")
    assert res.status_code == 200

def test_document_ingestion_and_search():
    doc_content = b"Local Knowledge Graph provides semantic search with SQLite FTS5 and graph traversal."
    files = {"file": ("readme_guide.txt", doc_content, "text/plain")}
    res = client.post("/api/v1/documents/upload", files=files)
    assert res.status_code == 200
    ingest_res = res.json()
    assert ingest_res["status"] == "ingested"
    doc_id = ingest_res["document_id"]

    # Deduplication test
    res_dup = client.post("/api/v1/documents/upload", files=files)
    assert res_dup.status_code == 200
    assert res_dup.json()["status"] == "duplicate"

    # Search fulltext
    res_search = client.post("/api/v1/search/query", json={"query": "semantic search", "mode": "fulltext"})
    assert res_search.status_code == 200
    assert res_search.json()["total_matches"] >= 1

    # Search semantic
    res_semantic = client.post("/api/v1/search/query", json={"query": "graph traversal", "mode": "semantic"})
    assert res_semantic.status_code == 200
    assert res_semantic.json()["total_matches"] >= 1

    # Search hybrid
    res_hybrid = client.post("/api/v1/search/query", json={"query": "SQLite", "mode": "hybrid"})
    assert res_hybrid.status_code == 200
    assert res_hybrid.json()["total_matches"] >= 1

def test_entities_and_relationships_and_graph(setup_test_db):
    # 1. Create entities
    res1 = client.post("/api/v1/entities", json={"name": "FastAPI", "entity_type": "Technology"})
    res2 = client.post("/api/v1/entities", json={"name": "Python", "entity_type": "Language"})
    res3 = client.post("/api/v1/entities", json={"name": "SQLite", "entity_type": "Database"})
    assert res1.status_code == 200
    assert res2.status_code == 200
    assert res3.status_code == 200

    e1_id = res1.json()["id"]
    e2_id = res2.json()["id"]
    e3_id = res3.json()["id"]

    # 2. Create relationships
    rel1 = client.post("/api/v1/graph/relationships", json={
        "source_id": e1_id,
        "target_id": e2_id,
        "relation_type": "BUILT_WITH"
    })
    rel2 = client.post("/api/v1/graph/relationships", json={
        "source_id": e1_id,
        "target_id": e3_id,
        "relation_type": "USES_DATABASE"
    })
    assert rel1.status_code == 200
    assert rel2.status_code == 200

    # 3. Overview
    overview = client.get("/api/v1/graph/overview").json()
    assert len(overview["nodes"]) >= 3
    assert len(overview["edges"]) >= 2

    # 4. Neighbors
    neighbors = client.get(f"/api/v1/graph/node/{e1_id}/neighbors?depth=1").json()
    assert len(neighbors["nodes"]) >= 3

    # 5. Path finding
    paths = client.get(f"/api/v1/graph/paths?source_id={e2_id}&target_id={e3_id}").json()
    assert paths["path"] is not None
    assert len(paths["path"]) == 2

    # 6. Entity Merge
    merge_res = client.post("/api/v1/entities/merge", json={
        "source_entity_id": e3_id,
        "target_entity_id": e2_id
    })
    assert merge_res.status_code == 200

def test_assistant_offline_rag():
    # Ingest note
    client.post("/api/v1/notes", json={
        "title": "Database Optimization Guide",
        "content": "SQLite WAL mode with PRAGMA synchronous = NORMAL accelerates write throughput significantly."
    })

    # Ask question
    res = client.post("/api/v1/ai/query", json={"question": "How to optimize SQLite writes?"})
    assert res.status_code == 200
    data = res.json()
    assert data["has_sufficient_evidence"] is True
    assert len(data["citations"]) >= 1

    # Ask completely unrelated question
    res_empty = client.post("/api/v1/ai/query", json={"question": "Quantum gravity string multiverse mechanics?"})
    assert res_empty.status_code == 200

def test_export_and_import():
    client.post("/api/v1/notes", json={"title": "Export Test Note", "content": "Sample content"})
    exp = client.get("/api/v1/system/export").json()
    assert exp["manifest"]["note_count"] >= 1

    imp = client.post("/api/v1/system/import", json=exp).json()
    assert imp["status"] == "success"
