import React, { useState, useCallback } from 'react';
import api from '../api';

/**
 * SummariseTab – YouTube URL input + PDF drag-drop upload.
 * Shows structured notes (Topic, Key Concepts, Detailed Notes, TL;DR)
 * after summarisation completes.
 */
export default function SummariseTab() {
  const [mode, setMode] = useState('youtube'); // 'youtube' | 'pdf'
  const [url, setUrl] = useState('');
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);
  const [polling, setPolling] = useState(false);

  // Polling for async tasks (Whisper fallback)
  React.useEffect(() => {
    let interval;
    if (result && result.summary_id?.startsWith('async_task_')) {
      const taskId = result.summary_id.replace('async_task_', '');
      setPolling(true);
      
      interval = setInterval(async () => {
        try {
          const taskStatus = await api.getTaskStatus(taskId);
          if (taskStatus.status === 'completed' && taskStatus.result) {
            setResult(taskStatus.result);
            setPolling(false);
            clearInterval(interval);
          } else if (taskStatus.status === 'failed') {
            setError(`Background task failed: ${taskStatus.error || 'Unknown error'}`);
            setPolling(false);
            clearInterval(interval);
          }
        } catch (err) {
          console.error("Polling error:", err);
        }
      }, 5000);
    }
    return () => clearInterval(interval);
  }, [result]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setResult(null);
    setLoading(true);

    try {
      let data;
      if (mode === 'youtube') {
        if (!url.trim()) throw new Error('Please enter a YouTube URL');
        data = await api.summarizeYouTube(url.trim());
      } else {
        if (!file) throw new Error('Please select a PDF file');
        data = await api.summarizePDF(file);
      }
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDrag = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') setDragActive(true);
    else if (e.type === 'dragleave') setDragActive(false);
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    const droppedFile = e.dataTransfer.files?.[0];
    if (droppedFile && droppedFile.name.toLowerCase().endsWith('.pdf')) {
      setFile(droppedFile);
      setError('');
    } else {
      setError('Please drop a PDF file');
    }
  }, []);

  const handleFileSelect = (e) => {
    const selected = e.target.files?.[0];
    if (selected) {
      setFile(selected);
      setError('');
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="section-title">Summarise Content</h2>
        <p className="text-sm text-gray-500 mt-1">Convert YouTube lectures or PDFs into structured study notes</p>
      </div>

      {/* Mode toggle */}
      <div className="glass-card">
        <div className="flex mb-6 rounded-xl p-1" style={{ background: 'rgba(255,255,255,0.04)' }}>
          <button
            type="button"
            onClick={() => { setMode('youtube'); setError(''); setResult(null); }}
            className={`flex-1 py-2.5 rounded-lg text-sm font-medium transition-all flex items-center justify-center gap-2 ${
              mode === 'youtube' ? 'bg-red-500/20 text-red-400' : 'text-gray-400 hover:text-gray-200'
            }`}
          >
            ▶️ YouTube
          </button>
          <button
            type="button"
            onClick={() => { setMode('pdf'); setError(''); setResult(null); }}
            className={`flex-1 py-2.5 rounded-lg text-sm font-medium transition-all flex items-center justify-center gap-2 ${
              mode === 'pdf' ? 'bg-blue-500/20 text-blue-400' : 'text-gray-400 hover:text-gray-200'
            }`}
          >
            📄 PDF Upload
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {mode === 'youtube' ? (
            <div>
              <label htmlFor="input-youtube-url" className="block text-xs font-medium text-gray-400 mb-1.5 uppercase tracking-wider">
                YouTube URL
              </label>
              <input
                id="input-youtube-url"
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                className="glass-input"
                placeholder="https://www.youtube.com/watch?v=..."
                required
              />
            </div>
          ) : (
            <div
              className={`drop-zone ${dragActive ? 'active' : ''}`}
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
              onClick={() => document.getElementById('input-pdf-file').click()}
            >
              <input
                id="input-pdf-file"
                type="file"
                accept=".pdf"
                onChange={handleFileSelect}
                className="hidden"
              />
              <div className="text-4xl mb-3">📁</div>
              {file ? (
                <p className="text-sm text-brand-400 font-medium">{file.name} ({(file.size / 1024 / 1024).toFixed(1)} MB)</p>
              ) : (
                <>
                  <p className="text-sm text-gray-400">Drag & drop your PDF here, or click to browse</p>
                  <p className="text-xs text-gray-600 mt-1">Max 50 MB</p>
                </>
              )}
            </div>
          )}

          {error && (
            <div className="rounded-xl bg-red-500/10 border border-red-500/20 px-4 py-3 text-sm text-red-400">
              {error}
            </div>
          )}

          <button
            id="btn-summarise"
            type="submit"
            disabled={loading}
            className="btn-primary w-full"
          >
            {loading ? (
              <><div className="spinner" style={{ width: 18, height: 18, borderWidth: 2 }} /> Generating notes...</>
            ) : (
              <>✨ Generate Study Notes</>
            )}
          </button>
        </form>
      </div>

      {/* Results */}
      {result && (
        <div className="space-y-4 animate-slide-up">
          {/* Time saved badge */}
          <div className="flex items-center gap-3">
            {polling ? (
              <span className="badge bg-amber-500/20 text-amber-400 animate-pulse">
                ⏳ Processing Background Task...
              </span>
            ) : (
              <span className="badge-green">⏱ {result.time_saved_minutes} min saved</span>
            )}
            <span className={result.source === 'youtube' ? 'badge-purple' : 'badge-blue'}>
              {result.source === 'youtube' ? '▶️ YouTube' : '📄 PDF'}
            </span>
          </div>

          {/* Topic */}
          <div className="glass-card">
            <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">Topic</h3>
            <p className="text-xl font-bold text-white">{result.notes.topic}</p>
          </div>

          {/* TL;DR */}
          <div className="glass-card" style={{ borderLeft: '3px solid #6366f1' }}>
            <h3 className="text-xs font-medium text-brand-400 uppercase tracking-wider mb-2">TL;DR</h3>
            <p className="text-sm text-gray-300 leading-relaxed">{result.notes.tldr}</p>
          </div>

          {/* Key Concepts */}
          <div className="glass-card">
            <h3 className="text-xs font-medium text-emerald-400 uppercase tracking-wider mb-3">Key Concepts</h3>
            <div className="text-sm text-gray-300 leading-relaxed whitespace-pre-line">
              {result.notes.key_concepts}
            </div>
          </div>

          {/* Detailed Notes */}
          <div className="glass-card">
            <h3 className="text-xs font-medium text-amber-400 uppercase tracking-wider mb-3">Detailed Notes</h3>
            <div className="text-sm text-gray-300 leading-relaxed whitespace-pre-line max-h-[500px] overflow-y-auto pr-2">
              {result.notes.detailed_notes}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
