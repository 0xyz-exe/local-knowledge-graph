import sqlite3
from typing import List, Dict, Any, Optional, Set, Tuple
from collections import deque

def get_graph_overview(conn: sqlite3.Connection, limit_nodes: int = 200) -> Dict[str, Any]:
    """Retrieve graph overview including nodes with calculated degrees and edges."""
    cursor = conn.cursor()

    # Fetch entities as nodes
    cursor.execute("""
    SELECT id, name, entity_type, description, confidence, is_user_created 
    FROM entities 
    LIMIT ?
    """, (limit_nodes,))
    entity_rows = cursor.fetchall()

    nodes: List[Dict[str, Any]] = []
    node_ids: Set[str] = set()

    for row in entity_rows:
        node_id = row["id"]
        node_ids.add(node_id)
        nodes.append({
            "id": node_id,
            "name": row["name"],
            "label": row["name"],
            "category": row["entity_type"],
            "node_type": "entity",
            "degree": 0
        })

    # Fetch relationships as edges connecting existing nodes
    cursor.execute("""
    SELECT id, source_id, target_id, relation_type, confidence 
    FROM relationships
    """)
    rel_rows = cursor.fetchall()

    edges: List[Dict[str, Any]] = []
    degrees: Dict[str, int] = {nid: 0 for nid in node_ids}

    for rel in rel_rows:
        src = rel["source_id"]
        tgt = rel["target_id"]
        if src in node_ids and tgt in node_ids:
            edges.append({
                "id": rel["id"],
                "source": src,
                "target": tgt,
                "relation": rel["relation_type"],
                "confidence": float(rel["confidence"])
            })
            degrees[src] = degrees.get(src, 0) + 1
            degrees[tgt] = degrees.get(tgt, 0) + 1

    # Attach computed degree
    for node in nodes:
        node["degree"] = degrees.get(node["id"], 0)

    # Global stats
    cursor.execute("SELECT COUNT(*) FROM entities")
    total_entities = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM relationships")
    total_relationships = cursor.fetchone()[0]

    return {
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "total_entities": total_entities,
            "total_relationships": total_relationships
        }
    }

def get_node_neighbors(conn: sqlite3.Connection, node_id: str, depth: int = 1) -> Dict[str, Any]:
    """Explore graph neighborhood around a specific entity up to given depth."""
    cursor = conn.cursor()

    visited_nodes: Set[str] = {node_id}
    frontier: Set[str] = {node_id}
    all_edges: List[Dict[str, Any]] = []

    for _ in range(depth):
        if not frontier:
            break
        placeholders = ",".join("?" for _ in frontier)
        query = f"""
        SELECT r.id, r.source_id, r.target_id, r.relation_type, r.confidence,
               s.name AS source_name, s.entity_type AS source_type,
               t.name AS target_name, t.entity_type AS target_type
        FROM relationships r
        JOIN entities s ON r.source_id = s.id
        JOIN entities t ON r.target_id = t.id
        WHERE r.source_id IN ({placeholders}) OR r.target_id IN ({placeholders})
        """
        params = list(frontier) + list(frontier)
        cursor.execute(query, params)
        rows = cursor.fetchall()

        next_frontier: Set[str] = set()
        for row in rows:
            edge_obj = {
                "id": row["id"],
                "source": row["source_id"],
                "source_name": row["source_name"],
                "target": row["target_id"],
                "target_name": row["target_name"],
                "relation": row["relation_type"],
                "confidence": float(row["confidence"])
            }
            if edge_obj not in all_edges:
                all_edges.append(edge_obj)

            for neighbor in (row["source_id"], row["target_id"]):
                if neighbor not in visited_nodes:
                    visited_nodes.add(neighbor)
                    next_frontier.add(neighbor)

        frontier = next_frontier

    # Fetch metadata for all discovered nodes
    if not visited_nodes:
        return {"nodes": [], "edges": []}

    placeholders = ",".join("?" for _ in visited_nodes)
    cursor.execute(f"SELECT id, name, entity_type, description FROM entities WHERE id IN ({placeholders})", list(visited_nodes))
    nodes = [
        {
            "id": r["id"],
            "name": r["name"],
            "label": r["name"],
            "category": r["entity_type"],
            "description": r["description"]
        }
        for r in cursor.fetchall()
    ]

    return {"center_id": node_id, "nodes": nodes, "edges": all_edges}

def find_shortest_path(conn: sqlite3.Connection, source_id: str, target_id: str) -> Optional[List[Dict[str, Any]]]:
    """Find shortest path between two nodes using Breadth-First Search (BFS)."""
    if source_id == target_id:
        return []

    cursor = conn.cursor()
    # Build adjacency list in-memory for active graph
    cursor.execute("SELECT source_id, target_id, relation_type FROM relationships")
    adj: Dict[str, List[Tuple[str, str]]] = {}
    for r in cursor.fetchall():
        s, t, rel = r["source_id"], r["target_id"], r["relation_type"]
        adj.setdefault(s, []).append((t, rel))
        adj.setdefault(t, []).append((s, rel))

    queue = deque([[source_id]])
    visited = {source_id}

    while queue:
        path = queue.popleft()
        current = path[-1]

        if current == target_id:
            # Construct detailed path
            detailed_path = []
            for i in range(len(path) - 1):
                u, v = path[i], path[i+1]
                cursor.execute("SELECT name, entity_type FROM entities WHERE id = ?", (u,))
                u_row = cursor.fetchone()
                cursor.execute("SELECT name, entity_type FROM entities WHERE id = ?", (v,))
                v_row = cursor.fetchone()
                
                detailed_path.append({
                    "step": i + 1,
                    "from_id": u,
                    "from_name": u_row["name"] if u_row else u,
                    "to_id": v,
                    "to_name": v_row["name"] if v_row else v
                })
            return detailed_path

        for neighbor, _ in adj.get(current, []):
            if neighbor not in visited:
                visited.add(neighbor)
                new_path = list(path)
                new_path.append(neighbor)
                queue.append(new_path)

    return None
