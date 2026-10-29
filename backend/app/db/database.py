import sqlite3
from typing import Generator, Optional
from contextlib import contextmanager
from backend.app.core.config import DB_PATH

def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    target_path = str(db_path or DB_PATH)
    conn = sqlite3.connect(target_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    return conn

@contextmanager
def get_db(db_path: Optional[str] = None) -> Generator[sqlite3.Connection, None, None]:
    conn = get_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db(db_path: Optional[str] = None):
    with get_db(db_path) as conn:
        cursor = conn.cursor()

        # Notes table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            tags TEXT DEFAULT '',
            category TEXT DEFAULT 'general',
            is_pinned INTEGER DEFAULT 0,
            is_archived INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Documents table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            file_type TEXT NOT NULL,
            file_size INTEGER NOT NULL,
            content_hash TEXT NOT NULL UNIQUE,
            file_path TEXT NOT NULL,
            extracted_text TEXT NOT NULL,
            chunk_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Document chunks table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS document_chunks (
            id TEXT PRIMARY KEY,
            document_id TEXT NOT NULL,
            chunk_index INTEGER NOT NULL,
            text TEXT NOT NULL,
            token_count INTEGER NOT NULL,
            vector_json TEXT DEFAULT '[]',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE
        );
        """)

        # Entities table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS entities (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE COLLATE NOCASE,
            entity_type TEXT NOT NULL,
            description TEXT DEFAULT '',
            aliases TEXT DEFAULT '[]',
            confidence REAL DEFAULT 1.0,
            is_user_created INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Entity mentions table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS entity_mentions (
            id TEXT PRIMARY KEY,
            entity_id TEXT NOT NULL,
            source_type TEXT NOT NULL, -- 'note' or 'document'
            source_id TEXT NOT NULL,
            snippet TEXT DEFAULT '',
            confidence REAL DEFAULT 1.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(entity_id) REFERENCES entities(id) ON DELETE CASCADE
        );
        """)

        # Relationships table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS relationships (
            id TEXT PRIMARY KEY,
            source_id TEXT NOT NULL,
            target_id TEXT NOT NULL,
            relation_type TEXT NOT NULL,
            confidence REAL DEFAULT 1.0,
            provenance TEXT DEFAULT 'manual',
            is_user_created INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(source_id) REFERENCES entities(id) ON DELETE CASCADE,
            FOREIGN KEY(target_id) REFERENCES entities(id) ON DELETE CASCADE,
            UNIQUE(source_id, target_id, relation_type)
        );
        """)

        # System settings table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # SQLite FTS5 Virtual Table for unified Full-Text Search
        cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS fts_index USING fts5(
            item_id UNINDEXED,
            item_type UNINDEXED, -- 'note', 'document', 'entity'
            title,
            content,
            tags,
            tokenize='porter unicode61'
        );
        """)

        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_notes_updated ON notes(updated_at DESC);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_docs_updated ON documents(updated_at DESC);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chunks_doc ON document_chunks(document_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_mentions_source ON entity_mentions(source_id, source_type);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_rel_source ON relationships(source_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_rel_target ON relationships(target_id);")
