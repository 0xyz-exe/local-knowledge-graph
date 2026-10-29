import os
import re
import uuid
import json
import hashlib
import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Tuple
from backend.app.core.config import DEFAULT_CHUNK_SIZE, DEFAULT_CHUNK_OVERLAP, UPLOADS_DIR
from backend.app.services.fts import update_fts_entry
from backend.app.services.semantic import generate_local_embedding
from backend.app.services.extractor import extract_entities_from_text

def compute_file_hash(content_bytes: bytes) -> str:
    """Compute SHA-256 digest of file contents for deduplication."""
    return hashlib.sha256(content_bytes).hexdigest()

def extract_text_from_file(filename: str, content_bytes: bytes) -> str:
    """Extract plain text from various file formats safely."""
    ext = Path(filename).suffix.lower()

    if ext in [".txt", ".md", ".markdown"]:
        return content_bytes.decode("utf-8", errors="replace")

    elif ext == ".json":
        try:
            parsed = json.loads(content_bytes.decode("utf-8", errors="replace"))
            return json.dumps(parsed, indent=2)
        except Exception:
            return content_bytes.decode("utf-8", errors="replace")

    elif ext == ".csv":
        return content_bytes.decode("utf-8", errors="replace")

    elif ext in [".html", ".htm"]:
        raw_text = content_bytes.decode("utf-8", errors="replace")
        # Strip html tags safely
        clean_text = re.sub(r"<[^>]+>", " ", raw_text)
        return " ".join(clean_text.split())

    else:
        # Generic text fallback
        try:
            return content_bytes.decode("utf-8", errors="replace")
        except Exception:
            return f"[Binary file: {filename} ({len(content_bytes)} bytes)]"

def chunk_text(text: str, chunk_size: int = DEFAULT_CHUNK_SIZE, overlap: int = DEFAULT_CHUNK_OVERLAP) -> List[str]:
    """Split long text into coherent overlapping chunks."""
    text = text.strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]

    chunks: List[str] = []
    start = 0
    step = chunk_size - overlap

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += step

    return chunks

def ingest_document(
    conn: sqlite3.Connection,
    filename: str,
    content_bytes: bytes
) -> Dict[str, Any]:
    """
    Ingest a document into local knowledge base:
    1. Check duplicates via SHA-256
    2. Extract normalized text
    3. Save file artifact
    4. Chunk text and generate dense vector embeddings
    5. Extract entities and record mentions
    6. Index in SQLite FTS5
    """
    content_hash = compute_file_hash(content_bytes)
    cursor = conn.cursor()

    # Deduplication check
    cursor.execute("SELECT id, filename FROM documents WHERE content_hash = ?", (content_hash,))
    existing = cursor.fetchone()
    if existing:
        return {
            "status": "duplicate",
            "document_id": existing["id"],
            "filename": existing["filename"],
            "message": f"Document '{filename}' is identical to existing document ID {existing['id']}."
        }

    doc_id = f"doc_{uuid.uuid4().hex[:12]}"
    file_type = Path(filename).suffix.lstrip(".").lower() or "txt"
    extracted_text = extract_text_from_file(filename, content_bytes)
    file_size = len(content_bytes)

    # Save to disk
    safe_disk_filename = f"{doc_id}_{filename}"
    saved_path = UPLOADS_DIR / safe_disk_filename
    with open(saved_path, "wb") as f:
        f.write(content_bytes)

    # Split into chunks
    text_chunks = chunk_text(extracted_text)
    chunk_count = len(text_chunks)

    # Insert document record
    cursor.execute("""
    INSERT INTO documents (id, filename, file_type, file_size, content_hash, file_path, extracted_text, chunk_count)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (doc_id, filename, file_type, file_size, content_hash, str(saved_path), extracted_text, chunk_count))

    # Insert chunks with local vector embeddings
    for idx, chunk in enumerate(text_chunks):
        chunk_id = f"chunk_{uuid.uuid4().hex[:12]}"
        vector = generate_local_embedding(chunk)
        cursor.execute("""
        INSERT INTO document_chunks (id, document_id, chunk_index, text, token_count, vector_json)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (chunk_id, doc_id, idx, chunk, len(chunk.split()), json.dumps(vector)))

    # Extract entities and record mentions
    extracted_entities = extract_entities_from_text(extracted_text)
    for ent in extracted_entities:
        ent_name = ent["name"]
        cursor.execute("SELECT id FROM entities WHERE name = ? COLLATE NOCASE", (ent_name,))
        ent_row = cursor.fetchone()
        if ent_row:
            ent_id = ent_row["id"]
        else:
            ent_id = f"ent_{uuid.uuid4().hex[:10]}"
            cursor.execute("""
            INSERT INTO entities (id, name, entity_type, description, confidence, is_user_created)
            VALUES (?, ?, ?, ?, ?, 0)
            """, (ent_id, ent_name, ent["entity_type"], ent["description"], ent["confidence"]))

        # Record mention
        mention_id = f"men_{uuid.uuid4().hex[:10]}"
        cursor.execute("""
        INSERT INTO entity_mentions (id, entity_id, source_type, source_id, snippet, confidence)
        VALUES (?, ?, 'document', ?, ?, ?)
        """, (mention_id, ent_id, doc_id, filename, ent["confidence"]))

    # Index into SQLite FTS5
    update_fts_entry(
        conn,
        item_id=doc_id,
        item_type="document",
        title=filename,
        content=extracted_text,
        tags=file_type
    )

    return {
        "status": "ingested",
        "document_id": doc_id,
        "filename": filename,
        "chunk_count": chunk_count,
        "entities_extracted": len(extracted_entities)
    }
