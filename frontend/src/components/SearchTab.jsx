import React, { useState } from 'react';
import api from '../api';

/**
 * SearchTab – Semantic search interface.
 * Allows users to search across all their notes with relevance scores.
 */
export default function SearchTab() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    setError('');
    setLoading(true);
    try {
      const data = await api.searchNotes(query.trim());
      setResults(data.results);
      if (data.results.length === 0) {
        setError('No matching notes found. Try a different query.');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="section-title">Semantic Search</h2>
        <p className="text-sm text-gray-500 mt-1">Search across the meaning of your notes, not just keywords</p>
      </div>

      {/* Search Input */}
      <div className="glass-card">
        <form onSubmit={handleSearch} className="relative">
          <input
            id="input-search-query"
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search for concepts, definitions, or specific topics..."
            className="glass-input !pr-16 !py-4"
          />
          <button
            id="btn-search-submit"
            type="submit"
            disabled={loading}
            className="absolute right-2 top-2 bottom-2 aspect-square btn-primary !p-0 !rounded-lg"
          >
            {loading ? (
               <div className="spinner" style={{ width: 16, height: 16, borderWidth: 2 }} />
            ) : (
              '🔍'
            )}
          </button>
        </form>
      </div>

      {/* Results */}
      <div className="space-y-4">
        {error && (
          <div className="rounded-xl bg-blue-500/5 border border-white/[0.05] px-4 py-8 text-center">
            <p className="text-gray-400 text-sm">{error}</p>
          </div>
        )}

        {results.map((res, idx) => (
          <div key={idx} className="glass-card animate-slide-up" style={{ animationDelay: `${idx * 50}ms` }}>
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
              <div className="flex items-center gap-3">
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center text-xs ${
                  res.source === 'youtube' ? 'bg-red-500/20 text-red-400' : 'bg-blue-500/20 text-blue-400'
                }`}>
                  {res.source === 'youtube' ? '▶️' : '📄'}
                </div>
                <div>
                  <h4 className="text-sm font-bold text-white line-clamp-1">{res.title}</h4>
                  <p className="text-[10px] text-gray-500 uppercase tracking-widest">{res.source}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <div className="text-[10px] text-gray-500 font-medium uppercase tracking-tighter">Match Confidence</div>
                <div className="w-24 h-1.5 bg-white/[0.05] rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-brand-500" 
                    style={{ width: `${res.relevance_score * 100}%` }}
                  ></div>
                </div>
                <span className="text-xs font-bold text-brand-400">{(res.relevance_score * 100).toFixed(0)}%</span>
              </div>
            </div>

            <div className="bg-white/[0.02] border border-white/[0.05] rounded-xl p-4">
              <p className="text-sm text-gray-300 leading-relaxed italic">
                "...{res.chunk_text}..."
              </p>
            </div>

            <div className="mt-4 flex justify-end">
              {res.source_url && (
                <a 
                  href={res.source_url} 
                  target="_blank" 
                  rel="noreferrer"
                  className="text-xs text-brand-400 hover:text-brand-300 transition-colors flex items-center gap-1"
                >
                  View Source ↗️
                </a>
              )}
            </div>
          </div>
        ))}

        {!loading && results.length === 0 && !error && (
          <div className="flex flex-col items-center justify-center py-20 opacity-20">
            <div className="text-6xl mb-4">🔎</div>
            <p className="text-lg font-medium">Ready to search</p>
          </div>
        )}
      </div>
    </div>
  );
}
