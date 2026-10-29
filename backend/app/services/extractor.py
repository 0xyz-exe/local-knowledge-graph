import re
from typing import List, Dict, Any, Set, Tuple

# Pre-defined known entity catalogs for deterministic offline NLP extraction
KNOWN_TECH = {
    "python", "typescript", "javascript", "sqlite", "fastapi", "react", "docker",
    "git", "linux", "tailwind", "vite", "pydantic", "playwright", "postgresql",
    "redis", "spacy", "ollama", "graphql", "rust", "c++", "go", "java"
}

KNOWN_ORGS = {
    "nous research", "github", "google", "microsoft", "apple", "anthropic",
    "openai", "apache", "mozilla", "meta", "hugging face", "amazon"
}

KNOWN_CONCEPTS = {
    "knowledge graph", "semantic search", "full-text search", "vector embedding",
    "retrieval-augmented generation", "rag", "natural language processing",
    "offline-first", "local-first", "reciprocal rank fusion", "cosine similarity",
    "knowledge vault", "graph discovery", "entity extraction"
}

def extract_wiki_links(text: str) -> List[str]:
    """Extract [[Note Title]] wiki links from markdown text."""
    matches = re.findall(r"\[\[(.*?)\]\]", text)
    links: List[str] = []
    for match in matches:
        title = match.split("|")[0].strip()
        if title and title not in links:
            links.append(title)
    return links

def extract_tags(text: str) -> List[str]:
    """Extract #tag hashtags from markdown text."""
    matches = re.findall(r"(?:^|\s)#([a-zA-Z0-9_\-]+)", text)
    tags: List[str] = []
    for tag in matches:
        tag_lower = tag.lower()
        if tag_lower not in tags:
            tags.append(tag_lower)
    return tags

def extract_entities_from_text(text: str) -> List[Dict[str, Any]]:
    """
    Deterministic rule-based and catalog entity extraction.
    100% offline, zero external API or heavy model requirement.
    Extracts Technology, Organization, Concept, and capitalized Title patterns.
    """
    found: Dict[str, Dict[str, Any]] = {}
    text_lower = text.lower()

    # 1. Match Known Technologies
    for tech in KNOWN_TECH:
        pattern = r"\b" + re.escape(tech) + r"\b"
        if re.search(pattern, text_lower):
            found[tech] = {
                "name": tech.capitalize() if len(tech) > 3 else tech.upper(),
                "entity_type": "Technology",
                "confidence": 0.95,
                "description": f"Technology identifier: {tech}"
            }

    # 2. Match Known Organizations
    for org in KNOWN_ORGS:
        pattern = r"\b" + re.escape(org) + r"\b"
        if re.search(pattern, text_lower):
            found[org] = {
                "name": " ".join(word.capitalize() for word in org.split()),
                "entity_type": "Organization",
                "confidence": 0.95,
                "description": f"Organization entity: {org}"
            }

    # 3. Match Known Concepts
    for concept in KNOWN_CONCEPTS:
        pattern = r"\b" + re.escape(concept) + r"\b"
        if re.search(pattern, text_lower):
            found[concept] = {
                "name": " ".join(word.capitalize() for word in concept.split()),
                "entity_type": "Concept",
                "confidence": 0.90,
                "description": f"Core concept: {concept}"
            }

    # 4. Extract Capitalized Named Entities (e.g. John Doe, Project Alpha)
    # Exclude sentence beginnings by looking for mid-sentence capitalization
    cap_pattern = r"(?<!\.\s)(?<!\n\n)\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b"
    for match in re.finditer(cap_pattern, text):
        phrase = match.group(1).strip()
        phrase_key = phrase.lower()
        if phrase_key not in found and len(phrase) > 3:
            # Simple heuristic: if contains 'Project' or 'System', mark Project; otherwise Person/Topic
            etype = "Project" if "project" in phrase_key or "system" in phrase_key else "Person"
            found[phrase_key] = {
                "name": phrase,
                "entity_type": etype,
                "confidence": 0.80,
                "description": f"Extracted named entity: {phrase}"
            }

    return list(found.values())
