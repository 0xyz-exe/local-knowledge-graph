import type {
  Note, DocumentItem, DocumentDetail, Entity, Relationship,
  GraphOverview, SearchResultItem, AIAskResponse, DashboardStats
} from './types';

const API_BASE = '/api/v1';

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, options);
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`API Error (${res.status}): ${errorText}`);
  }
  return res.json();
}

export const api = {
  // Stats
  getStats: () => fetchJson<DashboardStats>(`${API_BASE}/dashboard/stats`),

  // Notes
  getNotes: (params?: { tag?: string; category?: string; include_archived?: boolean }) => {
    const q = new URLSearchParams();
    if (params?.tag) q.set('tag', params.tag);
    if (params?.category) q.set('category', params.category);
    if (params?.include_archived) q.set('include_archived', 'true');
    return fetchJson<Note[]>(`${API_BASE}/notes?${q.toString()}`);
  },
  getNote: (id: string) => fetchJson<Note>(`${API_BASE}/notes/${id}`),
  createNote: (data: { title: string; content: string; tags?: string[]; category?: string; is_pinned?: boolean }) =>
    fetchJson<Note>(`${API_BASE}/notes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    }),
  updateNote: (id: string, data: Partial<Note>) =>
    fetchJson<Note>(`${API_BASE}/notes/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    }),
  deleteNote: (id: string) =>
    fetchJson<{ status: string; id: string }>(`${API_BASE}/notes/${id}`, { method: 'DELETE' }),

  // Documents
  getDocuments: () => fetchJson<DocumentItem[]>(`${API_BASE}/documents`),
  getDocument: (id: string) => fetchJson<DocumentDetail>(`${API_BASE}/documents/${id}`),
  uploadDocument: async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return fetchJson<{ status: string; document_id?: string; filename: string; chunk_count?: number }>(
      `${API_BASE}/documents/upload`,
      { method: 'POST', body: formData }
    );
  },
  deleteDocument: (id: string) =>
    fetchJson<{ status: string; id: string }>(`${API_BASE}/documents/${id}`, { method: 'DELETE' }),

  // Search
  search: (query: string, mode: string = 'hybrid', filter_type?: string) =>
    fetchJson<{ query: string; mode: string; total_matches: number; results: SearchResultItem[] }>(
      `${API_BASE}/search/query`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, mode, filter_type })
      }
    ),

  // Entities
  getEntities: (entity_type?: string) => {
    const q = entity_type ? `?entity_type=${encodeURIComponent(entity_type)}` : '';
    return fetchJson<Entity[]>(`${API_BASE}/entities${q}`);
  },
  createEntity: (data: { name: string; entity_type: string; description?: string }) =>
    fetchJson<Entity>(`${API_BASE}/entities`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    }),
  mergeEntities: (source_entity_id: string, target_entity_id: string) =>
    fetchJson<{ status: string; message: string }>(`${API_BASE}/entities/merge`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ source_entity_id, target_entity_id })
    }),
  deleteEntity: (id: string) =>
    fetchJson<{ status: string; id: string }>(`${API_BASE}/entities/${id}`, { method: 'DELETE' }),

  // Graph
  getGraphOverview: () => fetchJson<GraphOverview>(`${API_BASE}/graph/overview`),
  getNeighbors: (id: string, depth: number = 1) =>
    fetchJson<{ center_id: string; nodes: any[]; edges: any[] }>(`${API_BASE}/graph/node/${id}/neighbors?depth=${depth}`),
  findPaths: (source_id: string, target_id: string) =>
    fetchJson<{ source_id: string; target_id: string; path: any[] | null }>(
      `${API_BASE}/graph/paths?source_id=${source_id}&target_id=${target_id}`
    ),
  createRelationship: (data: { source_id: string; target_id: string; relation_type: string }) =>
    fetchJson<Relationship>(`${API_BASE}/graph/relationships`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    }),
  deleteRelationship: (id: string) =>
    fetchJson<{ status: string; id: string }>(`${API_BASE}/graph/relationships/${id}`, { method: 'DELETE' }),

  // AI Assistant
  askAssistant: (question: string) =>
    fetchJson<AIAskResponse>(`${API_BASE}/ai/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question })
    }),

  // System
  exportSystem: () => fetchJson<any>(`${API_BASE}/system/export`),
  importSystem: (data: any) =>
    fetchJson<{ status: string; imported_notes: number; imported_entities: number; imported_relationships: number }>(
      `${API_BASE}/system/import`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      }
    ),
  backupSystem: () => fetchJson<{ status: string; backup_path: string }>(`${API_BASE}/system/backup`, { method: 'POST' }),
  reindexSystem: () => fetchJson<{ status: string }>(`${API_BASE}/system/reindex`, { method: 'POST' })
};
