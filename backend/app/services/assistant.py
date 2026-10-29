import json
import sqlite3
from typing import List, Dict, Any, Tuple
from backend.app.services.fts import search_fts
from backend.app.services.semantic import generate_local_embedding, cosine_similarity
from backend.app.schemas.models import AICitation, AIAskResponse

def query_knowledge_assistant(
    conn: sqlite3.Connection,
    question: str,
    max_context_chunks: int = 5
) -> AIAskResponse:
    """
    Offline local knowledge assistant (RAG):
    1. Retrieves top matching chunks and notes using semantic & FTS ranking.
    2. Gathers graph context (related entities and relationships).
    3. Synthesizes a structured answer grounded strictly in retrieved sources.
    4. Attaches verifiable citations with exact excerpts.
    5. Returns transparent 'insufficient evidence' status if no context matches.
    """
    cursor = conn.cursor()
    question_clean = question.strip()
    if not question_clean:
        return AIAskResponse(
            question=question,
            answer="Please enter a specific question about your notes or documents.",
            has_sufficient_evidence=False,
            citations=[],
            graph_context=[]
        )

    # 1. Semantic chunk search
    query_vector = generate_local_embedding(question_clean)
    cursor.execute("""
    SELECT c.id, c.document_id, c.text, c.vector_json, d.filename 
    FROM document_chunks c
    JOIN documents d ON c.document_id = d.id
    """)
    chunk_rows = cursor.fetchall()

    scored_chunks: List[Tuple[float, Dict[str, Any]]] = []
    for row in chunk_rows:
        try:
            vec = json.loads(row["vector_json"])
            sim = cosine_similarity(query_vector, vec)
            if sim > 0.05:
                scored_chunks.append((sim, {
                    "source_id": row["document_id"],
                    "source_title": row["filename"],
                    "source_type": "document",
                    "excerpt": row["text"],
                    "relevance_score": round(sim, 4)
                }))
        except Exception:
            continue

    # Also check notes via semantic similarity and FTS
    cursor.execute("SELECT id, title, content FROM notes WHERE is_archived = 0")
    note_rows = cursor.fetchall()
    for n in note_rows:
        n_text = f"{n['title']}. {n['content']}"
        n_vec = generate_local_embedding(n_text)
        sim = cosine_similarity(query_vector, n_vec)
        if sim > 0.05:
            scored_chunks.append((sim, {
                "source_id": n["id"],
                "source_title": n["title"],
                "source_type": "note",
                "excerpt": n["content"][:400],
                "relevance_score": round(sim, 4)
            }))

    fts_note_matches = search_fts(conn, question_clean, filter_type="note", limit=5)
    for match in fts_note_matches:
        cursor.execute("SELECT content FROM notes WHERE id = ?", (match["item_id"],))
        n_row = cursor.fetchone()
        content = n_row["content"] if n_row else match["snippet"]
        scored_chunks.append((0.65, {
            "source_id": match["item_id"],
            "source_title": match["title"],
            "source_type": "note",
            "excerpt": content[:400],
            "relevance_score": 0.65
        }))

    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    top_chunks = [item[1] for item in scored_chunks[:max_context_chunks]]

    # 2. Graph Context: find related entities and relationships
    graph_context: List[str] = []
    cursor.execute("SELECT name, entity_type FROM entities")
    entities = cursor.fetchall()
    matched_entity_ids = []
    for ent in entities:
        if ent["name"].lower() in question_clean.lower():
            cursor.execute("SELECT id FROM entities WHERE name = ?", (ent["name"],))
            eid = cursor.fetchone()["id"]
            matched_entity_ids.append((eid, ent["name"], ent["entity_type"]))

    for eid, ename, etype in matched_entity_ids[:3]:
        cursor.execute("""
        SELECT r.relation_type, t.name AS target_name
        FROM relationships r
        JOIN entities t ON r.target_id = t.id
        WHERE r.source_id = ?
        LIMIT 4
        """, (eid,))
        for rel in cursor.fetchall():
            graph_context.append(f"{ename} ({etype}) --[{rel['relation_type']}]--> {rel['target_name']}")

    # 3. Answer synthesis
    citations = [
        AICitation(
            source_id=c["source_id"],
            source_title=c["source_title"],
            source_type=c["source_type"],
            excerpt=c["excerpt"][:280] + ("..." if len(c["excerpt"]) > 280 else ""),
            relevance_score=c["relevance_score"]
        )
        for c in top_chunks
    ]

    if not citations and not graph_context:
        return AIAskResponse(
            question=question,
            answer="The local knowledge base does not currently contain sufficient evidence to answer this question. Try adding notes or importing documents related to this topic.",
            has_sufficient_evidence=False,
            citations=[],
            graph_context=[]
        )

    # Synthesize grounded answer
    points: List[str] = []
    for idx, cit in enumerate(citations, start=1):
        clean_excerpt = " ".join(cit.excerpt.split())
        points.append(f"• According to [{cit.source_title}] ({cit.source_type}): \"{clean_excerpt}\"")

    if graph_context:
        graph_summary = " Connected knowledge graph paths: " + "; ".join(graph_context) + "."
    else:
        graph_summary = ""

    answer_text = (
        f"Based on your local knowledge base, here are the verified findings:\n\n"
        + "\n\n".join(points)
        + (f"\n\n**Graph Relationships:**\n{graph_summary}" if graph_summary else "")
    )

    return AIAskResponse(
        question=question,
        answer=answer_text,
        has_sufficient_evidence=True,
        citations=citations,
        graph_context=graph_context
    )
