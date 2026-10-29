import re
import sqlite3
from typing import List, Dict, Any, Optional

def sanitize_fts_query(query: str) -> str:
    """
    Sanitize user query for SQLite FTS5 syntax to prevent syntax errors.
    Filters common stop words when multiple tokens exist and joins with OR for high recall.
    """
    clean_tokens = re.findall(r"\w+", query, re.UNICODE)
    if not clean_tokens:
        return ""
    stop_words = {"how", "to", "the", "a", "an", "is", "in", "on", "of", "and", "or", "what", "which", "where", "with", "for", "by"}
    filtered = [t for t in clean_tokens if t.lower() not in stop_words] or clean_tokens
    return " OR ".join([f'"{token}"*' for token in filtered])

def update_fts_entry(
    conn: sqlite3.Connection,
    item_id: str,
    item_type: str,
    title: str,
    content: str,
    tags: str = ""
):
    """Update or insert an item into SQLite FTS5 table."""
    cursor = conn.cursor()
    # Remove existing entry if present
    cursor.execute("DELETE FROM fts_index WHERE item_id = ? AND item_type = ?", (item_id, item_type))
    cursor.execute(
        "INSERT INTO fts_index (item_id, item_type, title, content, tags) VALUES (?, ?, ?, ?, ?)",
        (item_id, item_type, title, content, tags)
    )

def delete_fts_entry(conn: sqlite3.Connection, item_id: str, item_type: str):
    """Delete an item from SQLite FTS5 table."""
    cursor = conn.cursor()
    cursor.execute("DELETE FROM fts_index WHERE item_id = ? AND item_type = ?", (item_id, item_type))

def search_fts(
    conn: sqlite3.Connection,
    query: str,
    filter_type: Optional[str] = None,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Execute full-text search against fts_index using BM25 ranking and snippet generation.
    """
    clean_q = sanitize_fts_query(query)
    if not clean_q:
        return []

    cursor = conn.cursor()
    
    if filter_type:
        sql = """
        SELECT 
            item_id, 
            item_type, 
            title, 
            snippet(fts_index, 3, '<mark>', '</mark>', '...', 25) AS snippet,
            bm25(fts_index) AS rank
        FROM fts_index
        WHERE fts_index MATCH ? AND item_type = ?
        ORDER BY rank
        LIMIT ?
        """
        cursor.execute(sql, (clean_q, filter_type, limit))
    else:
        sql = """
        SELECT 
            item_id, 
            item_type, 
            title, 
            snippet(fts_index, 3, '<mark>', '</mark>', '...', 25) AS snippet,
            bm25(fts_index) AS rank
        FROM fts_index
        WHERE fts_index MATCH ?
        ORDER BY rank
        LIMIT ?
        """
        cursor.execute(sql, (clean_q, limit))

    rows = cursor.fetchall()
    results = []
    for row in rows:
        # bm25 returns negative values where lower (more negative) is better.
        # Normalize score to positive range
        raw_rank = float(row["rank"])
        score = max(0.1, 10.0 / (1.0 + abs(raw_rank)))
        results.append({
            "item_id": row["item_id"],
            "item_type": row["item_type"],
            "title": row["title"],
            "snippet": row["snippet"] or row["title"],
            "score": round(score, 4),
            "match_type": "fulltext"
        })
    return results
