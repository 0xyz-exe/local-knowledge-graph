import json
import sqlite3
import shutil
import datetime
from pathlib import Path
from typing import Dict, Any, List
from backend.app.core.config import BACKUPS_DIR, DB_PATH
from backend.app.services.fts import update_fts_entry

def export_knowledge_json(conn: sqlite3.Connection) -> Dict[str, Any]:
    """Export complete knowledge base to a portable JSON manifest."""
    cursor = conn.cursor()

    cursor.execute("SELECT id, title, content, tags, category, is_pinned, is_archived, created_at, updated_at FROM notes")
    notes = [dict(r) for r in cursor.fetchall()]

    cursor.execute("SELECT id, filename, file_type, file_size, content_hash, extracted_text, chunk_count, created_at FROM documents")
    documents = [dict(r) for r in cursor.fetchall()]

    cursor.execute("SELECT id, name, entity_type, description, aliases, confidence, is_user_created, created_at FROM entities")
    entities = [dict(r) for r in cursor.fetchall()]

    cursor.execute("SELECT id, source_id, target_id, relation_type, confidence, provenance, is_user_created, created_at FROM relationships")
    relationships = [dict(r) for r in cursor.fetchall()]

    return {
        "version": "1.0",
        "exported_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "manifest": {
            "note_count": len(notes),
            "document_count": len(documents),
            "entity_count": len(entities),
            "relationship_count": len(relationships)
        },
        "notes": notes,
        "documents": documents,
        "entities": entities,
        "relationships": relationships
    }

def import_knowledge_json(conn: sqlite3.Connection, data: Dict[str, Any]) -> Dict[str, Any]:
    """Import and merge knowledge base from a JSON payload safely."""
    cursor = conn.cursor()
    imported_notes = 0
    imported_entities = 0
    imported_relationships = 0

    # 1. Notes
    for n in data.get("notes", []):
        cursor.execute("SELECT id FROM notes WHERE id = ?", (n["id"],))
        if not cursor.fetchone():
            cursor.execute("""
            INSERT INTO notes (id, title, content, tags, category, is_pinned, is_archived, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                n["id"], n["title"], n["content"], n.get("tags", ""),
                n.get("category", "general"), n.get("is_pinned", 0),
                n.get("is_archived", 0), n.get("created_at"), n.get("updated_at")
            ))
            update_fts_entry(conn, n["id"], "note", n["title"], n["content"], n.get("tags", ""))
            imported_notes += 1

    # 2. Entities
    entity_id_map: Dict[str, str] = {}
    for e in data.get("entities", []):
        cursor.execute("SELECT id FROM entities WHERE name = ? COLLATE NOCASE", (e["name"],))
        existing = cursor.fetchone()
        if existing:
            entity_id_map[e["id"]] = existing["id"]
        else:
            cursor.execute("""
            INSERT INTO entities (id, name, entity_type, description, aliases, confidence, is_user_created)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                e["id"], e["name"], e["entity_type"], e.get("description", ""),
                e.get("aliases", "[]"), e.get("confidence", 1.0), e.get("is_user_created", 1)
            ))
            entity_id_map[e["id"]] = e["id"]
            update_fts_entry(conn, e["id"], "entity", e["name"], e.get("description", ""), e["entity_type"])
            imported_entities += 1

    # 3. Relationships
    for r in data.get("relationships", []):
        src = entity_id_map.get(r["source_id"], r["source_id"])
        tgt = entity_id_map.get(r["target_id"], r["target_id"])
        if src and tgt and src != tgt:
            cursor.execute("""
            INSERT OR IGNORE INTO relationships (id, source_id, target_id, relation_type, confidence, provenance, is_user_created)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                r["id"], src, tgt, r["relation_type"],
                r.get("confidence", 1.0), r.get("provenance", "imported"),
                r.get("is_user_created", 1)
            ))
            imported_relationships += 1

    return {
        "status": "success",
        "imported_notes": imported_notes,
        "imported_entities": imported_entities,
        "imported_relationships": imported_relationships
    }

def create_db_backup() -> str:
    """Create a point-in-time timestamped backup of the SQLite database."""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = BACKUPS_DIR / f"lkg_backup_{timestamp}.sqlite3"
    shutil.copy2(DB_PATH, backup_file)
    return str(backup_file)
