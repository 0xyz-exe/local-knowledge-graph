import React, { useState, useEffect } from 'react';
import {
  LayoutDashboard, BookOpen, FileText, Search, Network,
  Brain, Settings as SettingsIcon, Plus, Trash2, Pin,
  Upload, Sparkles, RefreshCw, Download, Database, CheckCircle2,
  ChevronRight, Share2, Compass, FileCheck
} from 'lucide-react';
import { api } from './api';
import type {
  Note, DocumentItem, DocumentDetail, Entity,
  GraphOverview, GraphNode, SearchResultItem, AIAskResponse, DashboardStats
} from './types';
import { GraphCanvas } from './components/GraphCanvas';

export function App() {
  const [activeTab, setActiveTab] = useState<
    'dashboard' | 'vault' | 'documents' | 'search' | 'graph' | 'entities' | 'assistant' | 'settings'
  >('dashboard');

  // Global State
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [notes, setNotes] = useState<Note[]>([]);
  const [selectedNote, setSelectedNote] = useState<Note | null>(null);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selectedDoc, setSelectedDoc] = useState<DocumentDetail | null>(null);
  const [entities, setEntities] = useState<Entity[]>([]);
  const [graphData, setGraphData] = useState<GraphOverview | null>(null);
  const [selectedGraphNode, setSelectedGraphNode] = useState<GraphNode | null>(null);

  // Note editor form
  const [noteTitle, setNoteTitle] = useState('');
  const [noteContent, setNoteContent] = useState('');
  const [noteCategory, setNoteCategory] = useState('general');
  const [isEditingNote, setIsEditingNote] = useState(false);

  // Search state
  const [searchQuery, setSearchQuery] = useState('');
  const [searchMode, setSearchMode] = useState<'hybrid' | 'fulltext' | 'semantic'>('hybrid');
  const [searchResults, setSearchResults] = useState<SearchResultItem[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  // Assistant state
  const [assistantQuery, setAssistantQuery] = useState('');
  const [assistantResponse, setAssistantResponse] = useState<AIAskResponse | null>(null);
  const [isAsking, setIsAsking] = useState(false);

  // Graph pathfinder state
  const [pathSource, setPathSource] = useState('');
  const [pathTarget, setPathTarget] = useState('');
  const [pathResult, setPathResult] = useState<any[] | null>(null);

  // Entity modal state
  const [newEntityName, setNewEntityName] = useState('');
  const [newEntityType, setNewEntityType] = useState('Technology');
  const [mergeSourceId, setMergeSourceId] = useState('');
  const [mergeTargetId, setMergeTargetId] = useState('');

  // Notifications
  const [toast, setToast] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 3000);
  };

  const refreshAll = async () => {
    try {
      const [s, n, d, e, g] = await Promise.all([
        api.getStats(),
        api.getNotes(),
        api.getDocuments(),
        api.getEntities(),
        api.getGraphOverview()
      ]);
      setStats(s);
      setNotes(n);
      setDocuments(d);
      setEntities(e);
      setGraphData(g);
    } catch (err: any) {
      console.error('Failed to fetch data:', err);
    }
  };

  useEffect(() => {
    refreshAll();
  }, []);

  // Keyboard shortcut Ctrl+K / Cmd+K for search
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setActiveTab('search');
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Note actions
  const handleSaveNote = async () => {
    if (!noteTitle.trim()) {
      showToast('Note title is required');
      return;
    }
    try {
      if (selectedNote && isEditingNote) {
        await api.updateNote(selectedNote.id, {
          title: noteTitle,
          content: noteContent,
          category: noteCategory
        });
        showToast('Note updated successfully');
      } else {
        await api.createNote({
          title: noteTitle,
          content: noteContent,
          category: noteCategory
        });
        showToast('Note created successfully');
      }
      setNoteTitle('');
      setNoteContent('');
      setIsEditingNote(false);
      setSelectedNote(null);
      refreshAll();
    } catch (err: any) {
      showToast(`Error: ${err.message}`);
    }
  };

  const handleDeleteNote = async (id: string) => {
    if (!confirm('Are you sure you want to delete this note?')) return;
    try {
      await api.deleteNote(id);
      showToast('Note deleted');
      if (selectedNote?.id === id) {
        setSelectedNote(null);
        setIsEditingNote(false);
      }
      refreshAll();
    } catch (err: any) {
      showToast(`Error: ${err.message}`);
    }
  };

  // Document upload
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const res = await api.uploadDocument(file);
      if (res.status === 'duplicate') {
        showToast(`Duplicate: ${res.filename} already indexed`);
      } else {
        showToast(`Document ${res.filename} ingested (${res.chunk_count} chunks)`);
      }
      refreshAll();
    } catch (err: any) {
      showToast(`Upload failed: ${err.message}`);
    }
  };

  // Search execution
  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    setIsSearching(true);
    try {
      const res = await api.search(searchQuery, searchMode);
      setSearchResults(res.results);
    } catch (err: any) {
      showToast(`Search failed: ${err.message}`);
    } finally {
      setIsSearching(false);
    }
  };

  // Assistant query
  const handleAskAssistant = async () => {
    if (!assistantQuery.trim()) return;
    setIsAsking(true);
    try {
      const res = await api.askAssistant(assistantQuery);
      setAssistantResponse(res);
    } catch (err: any) {
      showToast(`Assistant error: ${err.message}`);
    } finally {
      setIsAsking(false);
    }
  };

  // Find graph path
  const handleFindPath = async () => {
    if (!pathSource || !pathTarget) return;
    try {
      const res = await api.findPaths(pathSource, pathTarget);
      setPathResult(res.path);
    } catch (err: any) {
      showToast(`Path error: ${err.message}`);
    }
  };

  // Create entity
  const handleCreateEntity = async () => {
    if (!newEntityName.trim()) return;
    try {
      await api.createEntity({ name: newEntityName, entity_type: newEntityType });
      showToast(`Entity '${newEntityName}' created`);
      setNewEntityName('');
      refreshAll();
    } catch (err: any) {
      showToast(`Error: ${err.message}`);
    }
  };

  // Merge entities
  const handleMergeEntities = async () => {
    if (!mergeSourceId || !mergeTargetId) return;
    try {
      const res = await api.mergeEntities(mergeSourceId, mergeTargetId);
      showToast(res.message);
      setMergeSourceId('');
      setMergeTargetId('');
      refreshAll();
    } catch (err: any) {
      showToast(`Merge failed: ${err.message}`);
    }
  };

  return (
    <div className="flex h-screen w-screen bg-slate-950 text-slate-100 font-sans overflow-hidden">
      {/* Toast Notification */}
      {toast && (
        <div className="fixed top-4 right-4 z-50 bg-blue-600 text-white text-xs px-4 py-2.5 rounded-lg shadow-2xl flex items-center gap-2 animate-bounce">
          <CheckCircle2 className="w-4 h-4" />
          <span>{toast}</span>
        </div>
      )}

      {/* Left Navigation Sidebar */}
      <aside className="w-64 bg-slate-900/90 border-r border-slate-800 flex flex-col justify-between shrink-0">
        <div>
          {/* Logo / Header */}
          <div className="p-4 border-b border-slate-800 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-blue-600/20 border border-blue-500/40 flex items-center justify-center text-blue-400">
                <Network className="w-5 h-5" />
              </div>
              <div>
                <h1 className="text-sm font-bold tracking-tight text-white leading-none">Local KG</h1>
                <span className="text-[10px] text-slate-400 font-mono">Knowledge OS</span>
              </div>
            </div>
            <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-medium">
              Offline
            </span>
          </div>

          {/* Navigation Links */}
          <nav className="p-3 space-y-1">
            {[
              { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
              { id: 'vault', label: 'Knowledge Vault', icon: BookOpen, count: stats?.total_notes },
              { id: 'documents', label: 'Documents', icon: FileText, count: stats?.total_documents },
              { id: 'search', label: 'Semantic Search', icon: Search, badge: 'Ctrl+K' },
              { id: 'graph', label: 'Knowledge Graph', icon: Network },
              { id: 'entities', label: 'Entities & Relations', icon: Compass, count: stats?.total_entities },
              { id: 'assistant', label: 'Knowledge Assistant', icon: Brain },
              { id: 'settings', label: 'System & Export', icon: SettingsIcon }
            ].map(item => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id as any)}
                  className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                    isActive
                      ? 'bg-blue-600 text-white shadow-md shadow-blue-600/20'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    <Icon className="w-4 h-4" />
                    <span>{item.label}</span>
                  </div>
                  {item.count !== undefined && (
                    <span className={`text-[10px] px-1.5 py-0.2 rounded-full font-mono ${
                      isActive ? 'bg-blue-700 text-blue-100' : 'bg-slate-800 text-slate-400'
                    }`}>
                      {item.count}
                    </span>
                  )}
                  {item.badge && (
                    <span className="text-[9px] px-1.5 py-0.5 rounded bg-slate-800/80 text-slate-400 border border-slate-700 font-mono">
                      {item.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </nav>
        </div>

        {/* Footer info */}
        <div className="p-3 border-t border-slate-800 bg-slate-950/40 text-[11px] text-slate-500">
          <div className="flex items-center justify-between mb-1">
            <span>SQLite FTS5</span>
            <span className="text-emerald-400">Active</span>
          </div>
          <div className="flex items-center justify-between">
            <span>Vector Engine</span>
            <span className="text-blue-400">Local 64-D</span>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col min-w-0 overflow-y-auto bg-slate-950">
        {/* ========================================================= */}
        {/* TAB 1: DASHBOARD */}
        {/* ========================================================= */}
        {activeTab === 'dashboard' && (
          <div className="p-8 max-w-6xl mx-auto w-full space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold tracking-tight text-white">Operations Dashboard</h2>
                <p className="text-xs text-slate-400 mt-1">Real-time local knowledge network telemetry & status</p>
              </div>
              <button
                onClick={refreshAll}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs rounded-lg border border-slate-700 transition-colors"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                Refresh
              </button>
            </div>

            {/* Metric Cards Grid */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              {[
                { title: 'Total Notes', value: stats?.total_notes ?? 0, icon: BookOpen, color: 'text-blue-400', desc: 'Markdown vault documents' },
                { title: 'Indexed Documents', value: stats?.total_documents ?? 0, icon: FileText, color: 'text-emerald-400', desc: `${stats?.total_chunks ?? 0} vectorized chunks` },
                { title: 'Knowledge Entities', value: stats?.total_entities ?? 0, icon: Compass, color: 'text-purple-400', desc: 'Discovered concepts & nodes' },
                { title: 'Relationships', value: stats?.total_relationships ?? 0, icon: Share2, color: 'text-cyan-400', desc: 'Interconnected edges' }
              ].map((card, i) => {
                const Icon = card.icon;
                return (
                  <div key={i} className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-sm">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs text-slate-400">{card.title}</span>
                      <Icon className={`w-4 h-4 ${card.color}`} />
                    </div>
                    <div className="text-2xl font-bold font-mono text-white mb-1">{card.value}</div>
                    <div className="text-[11px] text-slate-500">{card.desc}</div>
                  </div>
                );
              })}
            </div>

            {/* System Health & Quick Launch */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Storage & Engine */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
                <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-2">
                  <Database className="w-4 h-4 text-blue-400" />
                  Local Engine Status
                </h3>
                <div className="space-y-3 text-xs">
                  <div className="flex justify-between items-center pb-2 border-b border-slate-800">
                    <span className="text-slate-400">Database Engine</span>
                    <span className="font-mono text-slate-200">SQLite 3 (WAL Mode)</span>
                  </div>
                  <div className="flex justify-between items-center pb-2 border-b border-slate-800">
                    <span className="text-slate-400">Full-Text Tokenizer</span>
                    <span className="font-mono text-emerald-400">Porter Unicode61</span>
                  </div>
                  <div className="flex justify-between items-center pb-2 border-b border-slate-800">
                    <span className="text-slate-400">Vector Projection</span>
                    <span className="font-mono text-cyan-400">Cosine 64-D Hash</span>
                  </div>
                  <div className="flex justify-between items-center pb-2 border-b border-slate-800">
                    <span className="text-slate-400">On-Disk Footprint</span>
                    <span className="font-mono text-slate-300">
                      {Math.round((stats?.storage_size_bytes ?? 0) / 1024)} KB
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-slate-400">External AI Privacy</span>
                    <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 font-semibold border border-emerald-500/20">
                      Zero Outbound Calls
                    </span>
                  </div>
                </div>
              </div>

              {/* Recent Notes Preview */}
              <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-2">
                    <BookOpen className="w-4 h-4 text-emerald-400" />
                    Recent Notes
                  </h3>
                  <button
                    onClick={() => setActiveTab('vault')}
                    className="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1"
                  >
                    View Vault <ChevronRight className="w-3.5 h-3.5" />
                  </button>
                </div>
                {notes.length === 0 ? (
                  <p className="text-xs text-slate-500 py-6 text-center">No notes created yet. Go to Knowledge Vault to create one.</p>
                ) : (
                  <div className="space-y-2">
                    {notes.slice(0, 4).map(note => (
                      <div
                        key={note.id}
                        onClick={() => {
                          setSelectedNote(note);
                          setActiveTab('vault');
                        }}
                        className="p-3 bg-slate-950/60 hover:bg-slate-800/80 rounded-lg border border-slate-800/60 cursor-pointer transition-colors flex items-center justify-between"
                      >
                        <div>
                          <div className="text-xs font-medium text-slate-200">{note.title}</div>
                          <div className="text-[11px] text-slate-400 line-clamp-1 mt-0.5">{note.content}</div>
                        </div>
                        <span className="text-[10px] font-mono text-slate-500 shrink-0 ml-3">
                          {note.updated_at.split(' ')[0]}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* ========================================================= */}
        {/* TAB 2: KNOWLEDGE VAULT (NOTES) */}
        {/* ========================================================= */}
        {activeTab === 'vault' && (
          <div className="flex h-full">
            {/* Notes List Column */}
            <div className="w-80 border-r border-slate-800 flex flex-col bg-slate-900/60 shrink-0">
              <div className="p-4 border-b border-slate-800 flex items-center justify-between">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Vault Notes ({notes.length})</span>
                <button
                  onClick={() => {
                    setSelectedNote(null);
                    setNoteTitle('');
                    setNoteContent('');
                    setIsEditingNote(true);
                  }}
                  className="flex items-center gap-1 px-2.5 py-1 bg-blue-600 hover:bg-blue-500 text-white rounded text-xs transition-colors"
                >
                  <Plus className="w-3.5 h-3.5" /> New
                </button>
              </div>

              <div className="flex-1 overflow-y-auto p-2 space-y-1">
                {notes.map(note => (
                  <div
                    key={note.id}
                    onClick={() => {
                      setSelectedNote(note);
                      setNoteTitle(note.title);
                      setNoteContent(note.content);
                      setNoteCategory(note.category);
                      setIsEditingNote(false);
                    }}
                    className={`p-3 rounded-lg cursor-pointer transition-colors text-xs ${
                      selectedNote?.id === note.id
                        ? 'bg-blue-600/20 border border-blue-500/40 text-blue-200'
                        : 'hover:bg-slate-800 text-slate-300'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-semibold truncate">{note.title}</span>
                      {note.is_pinned && <Pin className="w-3 h-3 text-amber-400 shrink-0" />}
                    </div>
                    <div className="text-[11px] text-slate-400 line-clamp-2">{note.content}</div>
                    {note.tags.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-2">
                        {note.tags.map(t => (
                          <span key={t} className="text-[9px] px-1.5 py-0.2 bg-slate-800 text-slate-400 rounded">
                            #{t}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Note Editor / Preview Column */}
            <div className="flex-1 flex flex-col p-6 overflow-y-auto">
              {isEditingNote || selectedNote ? (
                <div className="space-y-4 max-w-3xl">
                  <div className="flex items-center justify-between">
                    <input
                      type="text"
                      placeholder="Note Title..."
                      value={noteTitle}
                      onChange={e => setNoteTitle(e.target.value)}
                      className="bg-slate-900 border border-slate-800 rounded-lg px-4 py-2 text-base font-semibold text-white w-2/3 focus:outline-none focus:border-blue-500"
                    />
                    <div className="flex items-center gap-2">
                      {selectedNote && !isEditingNote ? (
                        <button
                          onClick={() => setIsEditingNote(true)}
                          className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-xs rounded-lg border border-slate-700"
                        >
                          Edit
                        </button>
                      ) : (
                        <button
                          onClick={handleSaveNote}
                          className="px-4 py-1.5 bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold rounded-lg shadow-sm"
                        >
                          Save Note
                        </button>
                      )}
                      {selectedNote && (
                        <button
                          onClick={() => handleDeleteNote(selectedNote.id)}
                          className="p-1.5 text-red-400 hover:text-red-300 hover:bg-red-500/10 rounded-lg"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Content Area */}
                  {isEditingNote ? (
                    <textarea
                      placeholder="Write markdown here... Use [[Note Title]] for wiki links, #tags for tags."
                      value={noteContent}
                      onChange={e => setNoteContent(e.target.value)}
                      rows={14}
                      className="w-full bg-slate-900 border border-slate-800 rounded-lg p-4 font-mono text-xs text-slate-200 focus:outline-none focus:border-blue-500"
                    />
                  ) : (
                    <div className="bg-slate-900 border border-slate-800 rounded-lg p-5 text-xs text-slate-200 leading-relaxed whitespace-pre-wrap font-sans">
                      {selectedNote?.content}
                    </div>
                  )}

                  {/* Backlinks & Outgoing Links Panel */}
                  {selectedNote && (
                    <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-xl space-y-3">
                      <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Note Connections</h4>
                      <div className="grid grid-cols-2 gap-4 text-xs">
                        <div>
                          <span className="text-slate-500 block mb-1">Outgoing Links</span>
                          {selectedNote.outgoing_links?.length > 0 ? (
                            <div className="flex flex-wrap gap-1">
                              {selectedNote.outgoing_links.map(link => (
                                <span key={link} className="text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded border border-blue-500/20">
                                  [[{link}]]
                                </span>
                              ))}
                            </div>
                          ) : (
                            <span className="text-slate-500 italic">None</span>
                          )}
                        </div>
                        <div>
                          <span className="text-slate-500 block mb-1">Backlinks (Mentioned by)</span>
                          {selectedNote.backlinks?.length > 0 ? (
                            <div className="flex flex-wrap gap-1">
                              {selectedNote.backlinks.map(b => (
                                <span key={b.id} className="text-purple-400 bg-purple-500/10 px-2 py-0.5 rounded border border-purple-500/20">
                                  {b.title}
                                </span>
                              ))}
                            </div>
                          ) : (
                            <span className="text-slate-500 italic">None</span>
                          )}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="h-full flex items-center justify-center text-slate-500 text-xs">
                  Select a note from the left sidebar or create a new one.
                </div>
              )}
            </div>
          </div>
        )}

        {/* ========================================================= */}
        {/* TAB 3: DOCUMENTS & INGESTION */}
        {/* ========================================================= */}
        {activeTab === 'documents' && (
          <div className="p-8 max-w-6xl mx-auto w-full space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold tracking-tight text-white">Document Ingestion Engine</h2>
                <p className="text-xs text-slate-400 mt-1">Multi-format ingestion pipeline with chunking and content hashing</p>
              </div>
              <label className="flex items-center gap-1.5 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold rounded-lg cursor-pointer shadow-sm transition-colors">
                <Upload className="w-3.5 h-3.5" />
                Upload Document
                <input type="file" onChange={handleFileUpload} className="hidden" />
              </label>
            </div>

            {/* Document List Table */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-400 bg-slate-950/60">
                    <th className="py-3 px-4">Filename</th>
                    <th className="py-3 px-4">Format</th>
                    <th className="py-3 px-4">Size</th>
                    <th className="py-3 px-4">Chunks</th>
                    <th className="py-3 px-4">SHA-256 Hash</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {documents.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="py-8 text-center text-slate-500">
                        No documents imported yet. Click 'Upload Document' to add Markdown, TXT, JSON, CSV, or HTML files.
                      </td>
                    </tr>
                  ) : (
                    documents.map(doc => (
                      <tr key={doc.id} className="border-b border-slate-800/60 hover:bg-slate-800/40">
                        <td className="py-3 px-4 font-medium text-slate-200 flex items-center gap-2">
                          <FileText className="w-3.5 h-3.5 text-blue-400 shrink-0" />
                          {doc.filename}
                        </td>
                        <td className="py-3 px-4 font-mono text-slate-400 uppercase">{doc.file_type}</td>
                        <td className="py-3 px-4 text-slate-400 font-mono">{Math.round(doc.file_size / 1024)} KB</td>
                        <td className="py-3 px-4 text-emerald-400 font-mono">{doc.chunk_count} chunks</td>
                        <td className="py-3 px-4 text-slate-500 font-mono text-[10px]">{doc.content_hash.slice(0, 12)}...</td>
                        <td className="py-3 px-4 text-right space-x-2">
                          <button
                            onClick={async () => {
                              const d = await api.getDocument(doc.id);
                              setSelectedDoc(d);
                            }}
                            className="text-blue-400 hover:text-blue-300"
                          >
                            Inspect
                          </button>
                          <button
                            onClick={async () => {
                              await api.deleteDocument(doc.id);
                              showToast('Document removed');
                              refreshAll();
                            }}
                            className="text-red-400 hover:text-red-300"
                          >
                            Delete
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {/* Document Detail Modal / Drawer */}
            {selectedDoc && (
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-4">
                <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                  <h3 className="text-sm font-bold text-white flex items-center gap-2">
                    <FileCheck className="w-4 h-4 text-emerald-400" />
                    Document Inspector: {selectedDoc.filename}
                  </h3>
                  <button
                    onClick={() => setSelectedDoc(null)}
                    className="text-xs text-slate-400 hover:text-white"
                  >
                    Close
                  </button>
                </div>

                <div className="space-y-2">
                  <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Extracted Vector Chunks ({selectedDoc.chunks.length})</span>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-h-80 overflow-y-auto">
                    {selectedDoc.chunks.map(chunk => (
                      <div key={chunk.id} className="p-3 bg-slate-950/70 border border-slate-800/80 rounded-lg text-xs space-y-1">
                        <div className="flex justify-between text-[10px] text-slate-500 font-mono">
                          <span>Chunk #{chunk.chunk_index}</span>
                          <span>{chunk.token_count} words</span>
                        </div>
                        <p className="text-slate-300 text-[11px] leading-relaxed line-clamp-4">{chunk.text}</p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ========================================================= */}
        {/* TAB 4: SEMANTIC SEARCH */}
        {/* ========================================================= */}
        {activeTab === 'search' && (
          <div className="p-8 max-w-4xl mx-auto w-full space-y-6">
            <div>
              <h2 className="text-xl font-bold tracking-tight text-white">Semantic & Hybrid Search</h2>
              <p className="text-xs text-slate-400 mt-1">Combine SQLite FTS5 lexical ranking with local vector cosine similarity</p>
            </div>

            {/* Search Input Box */}
            <div className="space-y-3">
              <div className="flex gap-2">
                <div className="relative flex-1">
                  <Search className="w-4 h-4 absolute left-3.5 top-3 text-slate-400" />
                  <input
                    type="text"
                    placeholder="Search documents, notes, entities, and concepts..."
                    value={searchQuery}
                    onChange={e => setSearchQuery(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && handleSearch()}
                    className="w-full bg-slate-900 border border-slate-800 rounded-xl pl-10 pr-4 py-2.5 text-xs text-white focus:outline-none focus:border-blue-500 shadow-inner"
                  />
                </div>
                <button
                  onClick={handleSearch}
                  disabled={isSearching}
                  className="px-5 py-2.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-xs font-semibold rounded-xl shadow-sm transition-colors flex items-center gap-2"
                >
                  {isSearching ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Search className="w-3.5 h-3.5" />}
                  Search
                </button>
              </div>

              {/* Mode Selector */}
              <div className="flex items-center gap-2 text-xs">
                <span className="text-slate-500 text-[11px]">Mode:</span>
                {(['hybrid', 'fulltext', 'semantic'] as const).map(mode => (
                  <button
                    key={mode}
                    onClick={() => setSearchMode(mode)}
                    className={`px-3 py-1 rounded-lg text-xs capitalize transition-colors ${
                      searchMode === mode
                        ? 'bg-blue-600/20 text-blue-300 border border-blue-500/40 font-semibold'
                        : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
                    }`}
                  >
                    {mode === 'hybrid' ? 'Hybrid (RRF)' : mode}
                  </button>
                ))}
              </div>
            </div>

            {/* Results List */}
            <div className="space-y-3">
              <div className="flex justify-between items-center text-xs text-slate-400">
                <span>Results ({searchResults.length})</span>
                {searchResults.length > 0 && <span className="font-mono text-[10px]">Ranked via {searchMode}</span>}
              </div>

              {searchResults.length === 0 ? (
                <div className="p-8 text-center text-slate-500 text-xs bg-slate-900/40 border border-slate-800 rounded-xl">
                  {searchQuery ? 'No matching records found in knowledge base.' : 'Type a query above to execute instant local search.'}
                </div>
              ) : (
                searchResults.map((item, idx) => (
                  <div key={idx} className="p-4 bg-slate-900 border border-slate-800 rounded-xl space-y-1.5 shadow-sm">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 uppercase font-mono">
                          {item.item_type}
                        </span>
                        <h4 className="text-xs font-bold text-slate-100">{item.title}</h4>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] font-mono text-emerald-400">Score: {item.score}</span>
                        <span className="text-[10px] px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20 font-medium">
                          {item.match_type}
                        </span>
                      </div>
                    </div>
                    <p className="text-xs text-slate-300 leading-relaxed font-sans">
                      {item.snippet.replace(/<[^>]+>/g, '')}
                    </p>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {/* ========================================================= */}
        {/* TAB 5: KNOWLEDGE GRAPH */}
        {/* ========================================================= */}
        {activeTab === 'graph' && (
          <div className="p-8 max-w-6xl mx-auto w-full space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold tracking-tight text-white">Interactive Knowledge Graph</h2>
                <p className="text-xs text-slate-400 mt-1">Force-directed visualization with BFS shortest pathfinder and neighborhood expansion</p>
              </div>
            </div>

            {/* Interactive Graph Canvas */}
            <GraphCanvas
              nodes={graphData?.nodes || []}
              edges={graphData?.edges || []}
              selectedNodeId={selectedGraphNode?.id}
              onSelectNode={setSelectedGraphNode}
            />

            {/* Selected Node Details & Pathfinder */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Selected Node Inspector */}
              <div className="p-5 bg-slate-900 border border-slate-800 rounded-xl space-y-3">
                <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-2">
                  <Compass className="w-4 h-4 text-blue-400" />
                  Node Inspector
                </h3>
                {selectedGraphNode ? (
                  <div className="space-y-2 text-xs">
                    <div className="flex justify-between items-center pb-2 border-b border-slate-800">
                      <span className="text-slate-400">Name</span>
                      <span className="font-bold text-white">{selectedGraphNode.name}</span>
                    </div>
                    <div className="flex justify-between items-center pb-2 border-b border-slate-800">
                      <span className="text-slate-400">Category</span>
                      <span className="text-purple-400 font-medium">{selectedGraphNode.category}</span>
                    </div>
                    <div className="flex justify-between items-center pb-2 border-b border-slate-800">
                      <span className="text-slate-400">Degree Centrality</span>
                      <span className="font-mono text-emerald-400">{selectedGraphNode.degree} connections</span>
                    </div>
                  </div>
                ) : (
                  <p className="text-xs text-slate-500 py-4">Click any node on the graph canvas to inspect its metadata and connections.</p>
                )}
              </div>

              {/* BFS Path Finder */}
              <div className="p-5 bg-slate-900 border border-slate-800 rounded-xl space-y-3">
                <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-2">
                  <Network className="w-4 h-4 text-cyan-400" />
                  Shortest Path Explorer (BFS)
                </h3>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <select
                    value={pathSource}
                    onChange={e => setPathSource(e.target.value)}
                    className="bg-slate-950 border border-slate-800 rounded-lg p-2 text-slate-200 text-xs"
                  >
                    <option value="">Select Origin...</option>
                    {graphData?.nodes.map(n => (
                      <option key={n.id} value={n.id}>{n.name}</option>
                    ))}
                  </select>
                  <select
                    value={pathTarget}
                    onChange={e => setPathTarget(e.target.value)}
                    className="bg-slate-950 border border-slate-800 rounded-lg p-2 text-slate-200 text-xs"
                  >
                    <option value="">Select Target...</option>
                    {graphData?.nodes.map(n => (
                      <option key={n.id} value={n.id}>{n.name}</option>
                    ))}
                  </select>
                </div>
                <button
                  onClick={handleFindPath}
                  className="w-full py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-semibold transition-colors"
                >
                  Calculate Shortest Path
                </button>
                {pathResult && (
                  <div className="p-3 bg-slate-950/80 rounded-lg border border-slate-800 text-xs space-y-1">
                    <span className="text-[10px] text-slate-500 uppercase font-mono">Discovered Path:</span>
                    {pathResult.map((p, idx) => (
                      <div key={idx} className="flex items-center gap-2 text-slate-300">
                        <span className="text-blue-400 font-mono">#{p.step}</span>
                        <span>{p.from_name}</span>
                        <span className="text-slate-500">→</span>
                        <span className="font-semibold text-white">{p.to_name}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* ========================================================= */}
        {/* TAB 6: ENTITIES & RELATIONS */}
        {/* ========================================================= */}
        {activeTab === 'entities' && (
          <div className="p-8 max-w-6xl mx-auto w-full space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold tracking-tight text-white">Entities & Relationships</h2>
                <p className="text-xs text-slate-400 mt-1">Manage discovered entities, aliases, merges, and manual graph edges</p>
              </div>
            </div>

            {/* Entity Creation & Merge Controls */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Create Entity */}
              <div className="p-4 bg-slate-900 border border-slate-800 rounded-xl space-y-3">
                <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider block">Create Custom Entity</span>
                <div className="flex gap-2">
                  <input
                    type="text"
                    placeholder="Entity Name (e.g. SQLite, Docker)..."
                    value={newEntityName}
                    onChange={e => setNewEntityName(e.target.value)}
                    className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-white"
                  />
                  <select
                    value={newEntityType}
                    onChange={e => setNewEntityType(e.target.value)}
                    className="bg-slate-950 border border-slate-800 rounded-lg px-2 py-1.5 text-xs text-slate-200"
                  >
                    <option value="Technology">Technology</option>
                    <option value="Organization">Organization</option>
                    <option value="Concept">Concept</option>
                    <option value="Project">Project</option>
                    <option value="Person">Person</option>
                  </select>
                  <button
                    onClick={handleCreateEntity}
                    className="px-4 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-medium"
                  >
                    Add
                  </button>
                </div>
              </div>

              {/* Merge Entities */}
              <div className="p-4 bg-slate-900 border border-slate-800 rounded-xl space-y-3">
                <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider block">Merge Duplicate Entities</span>
                <div className="flex gap-2">
                  <select
                    value={mergeSourceId}
                    onChange={e => setMergeSourceId(e.target.value)}
                    className="flex-1 bg-slate-950 border border-slate-800 rounded-lg p-1.5 text-xs text-slate-200"
                  >
                    <option value="">Merge Source...</option>
                    {entities.map(e => <option key={e.id} value={e.id}>{e.name}</option>)}
                  </select>
                  <span className="text-slate-500 self-center">into</span>
                  <select
                    value={mergeTargetId}
                    onChange={e => setMergeTargetId(e.target.value)}
                    className="flex-1 bg-slate-950 border border-slate-800 rounded-lg p-1.5 text-xs text-slate-200"
                  >
                    <option value="">Target Entity...</option>
                    {entities.map(e => <option key={e.id} value={e.id}>{e.name}</option>)}
                  </select>
                  <button
                    onClick={handleMergeEntities}
                    className="px-3 py-1.5 bg-amber-600 hover:bg-amber-500 text-white rounded-lg text-xs font-medium"
                  >
                    Merge
                  </button>
                </div>
              </div>
            </div>

            {/* Entities Table */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-400 bg-slate-950/60">
                    <th className="py-3 px-4">Entity Name</th>
                    <th className="py-3 px-4">Category</th>
                    <th className="py-3 px-4">Mentions</th>
                    <th className="py-3 px-4">Relations</th>
                    <th className="py-3 px-4">Provenance</th>
                    <th className="py-3 px-4 text-right">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {entities.map(ent => (
                    <tr key={ent.id} className="border-b border-slate-800/60 hover:bg-slate-800/40">
                      <td className="py-2.5 px-4 font-semibold text-slate-200">{ent.name}</td>
                      <td className="py-2.5 px-4">
                        <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-slate-800 text-slate-300">
                          {ent.entity_type}
                        </span>
                      </td>
                      <td className="py-2.5 px-4 font-mono text-slate-400">{ent.mention_count}</td>
                      <td className="py-2.5 px-4 font-mono text-cyan-400">{ent.relationship_count}</td>
                      <td className="py-2.5 px-4 text-[10px] text-slate-500 font-mono">
                        {ent.is_user_created ? 'Manual' : 'NLP Extracted'}
                      </td>
                      <td className="py-2.5 px-4 text-right">
                        <button
                          onClick={async () => {
                            await api.deleteEntity(ent.id);
                            showToast(`Entity '${ent.name}' deleted`);
                            refreshAll();
                          }}
                          className="text-red-400 hover:text-red-300"
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* ========================================================= */}
        {/* TAB 7: KNOWLEDGE ASSISTANT */}
        {/* ========================================================= */}
        {activeTab === 'assistant' && (
          <div className="p-8 max-w-4xl mx-auto w-full space-y-6">
            <div>
              <h2 className="text-xl font-bold tracking-tight text-white">Local Knowledge Assistant</h2>
              <p className="text-xs text-slate-400 mt-1">
                Offline Retrieval-Augmented Generation (RAG) backed by your private notes, documents, and knowledge graph
              </p>
            </div>

            {/* Prompt Form */}
            <div className="p-5 bg-slate-900 border border-slate-800 rounded-xl space-y-4 shadow-sm">
              <div className="space-y-2">
                <label className="text-xs font-semibold text-slate-300 flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-blue-400" />
                  Ask question against local knowledge base
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    placeholder="e.g. How to optimize SQLite writes? Or summarize my notes about FastAPI architecture..."
                    value={assistantQuery}
                    onChange={e => setAssistantQuery(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && handleAskAssistant()}
                    className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-blue-500"
                  />
                  <button
                    onClick={handleAskAssistant}
                    disabled={isAsking}
                    className="px-6 py-2.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-xs font-semibold rounded-xl shadow-sm transition-colors flex items-center gap-2"
                  >
                    {isAsking ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Brain className="w-3.5 h-3.5" />}
                    Synthesize
                  </button>
                </div>
              </div>
            </div>

            {/* Assistant Response Box */}
            {assistantResponse && (
              <div className="p-6 bg-slate-900 border border-slate-800 rounded-xl space-y-4 shadow-md">
                <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                  <span className="text-xs font-bold text-white flex items-center gap-2">
                    <Brain className="w-4 h-4 text-blue-400" />
                    Synthesized Answer
                  </span>
                  <span className={`text-[10px] px-2 py-0.5 rounded font-medium border ${
                    assistantResponse.has_sufficient_evidence
                      ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                      : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                  }`}>
                    {assistantResponse.has_sufficient_evidence ? 'Grounded with Evidence' : 'Insufficient Evidence'}
                  </span>
                </div>

                <div className="text-xs text-slate-200 leading-relaxed whitespace-pre-wrap font-sans">
                  {assistantResponse.answer}
                </div>

                {/* Verifiable Citations */}
                {assistantResponse.citations.length > 0 && (
                  <div className="pt-4 border-t border-slate-800 space-y-2">
                    <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                      Verifiable Source Citations ({assistantResponse.citations.length})
                    </span>
                    <div className="space-y-2">
                      {assistantResponse.citations.map((c, i) => (
                        <div key={i} className="p-3 bg-slate-950/60 border border-slate-800/80 rounded-lg text-xs space-y-1">
                          <div className="flex justify-between items-center text-[11px]">
                            <span className="font-semibold text-blue-400">[{c.source_title}] ({c.source_type})</span>
                            <span className="text-slate-500 font-mono text-[10px]">Relevance: {c.relevance_score}</span>
                          </div>
                          <p className="text-slate-400 text-[11px] italic">"{c.excerpt}"</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* ========================================================= */}
        {/* TAB 8: SYSTEM & EXPORT */}
        {/* ========================================================= */}
        {activeTab === 'settings' && (
          <div className="p-8 max-w-4xl mx-auto w-full space-y-6">
            <div>
              <h2 className="text-xl font-bold tracking-tight text-white">System & Data Portability</h2>
              <p className="text-xs text-slate-400 mt-1">Export complete knowledge base, create SQLite backups, and trigger index rebuilds</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Export JSON */}
              <div className="p-5 bg-slate-900 border border-slate-800 rounded-xl space-y-3">
                <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-2">
                  <Download className="w-4 h-4 text-emerald-400" />
                  Export Knowledge Base
                </h3>
                <p className="text-xs text-slate-400">
                  Download portable JSON bundle containing all notes, documents, entities, and graph relationships.
                </p>
                <button
                  onClick={async () => {
                    const data = await api.exportSystem();
                    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `local_knowledge_graph_export_${new Date().toISOString().slice(0, 10)}.json`;
                    a.click();
                    showToast('Export downloaded');
                  }}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-semibold"
                >
                  Download JSON Export
                </button>
              </div>

              {/* Point-in-time Backup */}
              <div className="p-5 bg-slate-900 border border-slate-800 rounded-xl space-y-3">
                <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-2">
                  <Database className="w-4 h-4 text-blue-400" />
                  Create Database Backup
                </h3>
                <p className="text-xs text-slate-400">
                  Creates an exact point-in-time timestamped copy of your SQLite WAL database in the backups folder.
                </p>
                <button
                  onClick={async () => {
                    const res = await api.backupSystem();
                    showToast(`Backup created: ${res.backup_path}`);
                  }}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-semibold"
                >
                  Create SQLite Backup
                </button>
              </div>
            </div>

            {/* Reindex action */}
            <div className="p-5 bg-slate-900 border border-slate-800 rounded-xl space-y-3">
              <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-2">
                <RefreshCw className="w-4 h-4 text-cyan-400" />
                Rebuild Full-Text Index
              </h3>
              <p className="text-xs text-slate-400">
                Purges and synchronizes SQLite FTS5 index across all active notes, documents, and entities.
              </p>
              <button
                onClick={async () => {
                  await api.reindexSystem();
                  showToast('FTS5 index successfully rebuilt');
                  refreshAll();
                }}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg text-xs font-semibold"
              >
                Trigger Re-index
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
