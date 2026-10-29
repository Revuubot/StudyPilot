import React, { useState, useRef, useEffect } from 'react';
import api from '../api';

/**
 * AskTab – RAG question answering interface.
 * Uses WebSockets for streaming responses and shows citations.
 */
export default function AskTab() {
  const [query, setQuery] = useState('');
  const [messages, setMessages] = useState([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [status, setStatus] = useState('');
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, status]);

  const handleAsk = (e) => {
    e.preventDefault();
    if (!query.trim() || isStreaming) return;

    const userQuery = query.trim();
    setQuery('');
    setIsStreaming(true);
    setStatus('Connecting...');

    // Add user message
    setMessages((prev) => [...prev, { type: 'user', content: userQuery }]);

    // Prepare assistant message placeholder
    let currentAssistantMessage = { type: 'assistant', content: '', citations: [], latency: null };
    setMessages((prev) => [...prev, currentAssistantMessage]);

    const updateLastAssistantMessage = (updates) => {
      setMessages((prev) => {
        const newMessages = [...prev];
        const last = { ...newMessages[newMessages.length - 1], ...updates };
        newMessages[newMessages.length - 1] = last;
        return newMessages;
      });
    };

    api.connectWebSocket(userQuery, {
      onStatus: (msg) => setStatus(msg),
      onChunk: (chunk) => {
        currentAssistantMessage.content += chunk;
        updateLastAssistantMessage({ content: currentAssistantMessage.content });
      },
      onCitations: (citations) => {
        currentAssistantMessage.citations = citations;
        updateLastAssistantMessage({ citations });
      },
      onDone: (latency) => {
        updateLastAssistantMessage({ latency });
        setIsStreaming(false);
        setStatus('');
      },
      onError: (err) => {
        updateLastAssistantMessage({ content: `Error: ${err}`, type: 'error' });
        setIsStreaming(false);
        setStatus('');
      },
    });
  };

  return (
    <div className="flex flex-col h-[calc(100vh-12rem)] space-y-4">
      <div>
        <h2 className="section-title">Ask StudyPilot</h2>
        <p className="text-sm text-gray-500 mt-1">Get instant answers with citations from your study notes</p>
      </div>

      {/* Chat window */}
      <div 
        ref={scrollRef}
        className="flex-1 glass-card overflow-y-auto space-y-6 p-4 sm:p-6"
      >
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center opacity-40">
            <div className="text-6xl mb-4">💬</div>
            <p className="text-lg font-medium">No questions yet</p>
            <p className="text-sm max-w-xs">Ask something like "Explain the main concept of the lecture" or "What are the key takeaways?"</p>
          </div>
        ) : (
          messages.map((msg, idx) => (
            <div key={idx} className={`flex ${msg.type === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[85%] space-y-3 ${msg.type === 'user' ? 'animate-slide-up' : ''}`}>
                {/* Message bubble */}
                <div className={`rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                  msg.type === 'user' 
                    ? 'bg-brand-600 text-white shadow-lg shadow-brand-900/20' 
                    : msg.type === 'error'
                      ? 'bg-red-500/10 border border-red-500/20 text-red-400'
                      : 'bg-white/[0.04] border border-white/[0.08] text-gray-200'
                }`}>
                  {msg.content}
                  {!msg.content && msg.type === 'assistant' && (
                    <div className="flex gap-1 py-1">
                      <div className="w-1.5 h-1.5 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                      <div className="w-1.5 h-1.5 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                      <div className="w-1.5 h-1.5 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                    </div>
                  )}
                </div>

                {/* Citations */}
                {msg.citations && msg.citations.length > 0 && (
                  <div className="flex flex-wrap gap-2 animate-fade-in">
                    {msg.citations.map((cite, cIdx) => (
                      <div key={cIdx} className="group relative">
                        <span className="badge bg-white/[0.05] text-xs text-gray-400 border border-white/[0.1] hover:bg-white/[0.1] cursor-help">
                          [{cIdx + 1}] {cite.source_title.slice(0, 20)}...
                        </span>
                        {/* Tooltip */}
                        <div className="absolute bottom-full left-0 mb-2 w-64 glass-card p-3 text-xs hidden group-hover:block z-50 animate-slide-up">
                          <p className="font-bold text-white mb-1">{cite.source_title}</p>
                          <p className="text-gray-400 italic line-clamp-3">"{cite.chunk_text}"</p>
                          <div className="mt-2 flex justify-between items-center">
                            <span className="text-[10px] text-brand-400">Score: {(cite.relevance_score * 100).toFixed(0)}%</span>
                            {cite.source_url && (
                              <a href={cite.source_url} target="_blank" rel="noreferrer" className="text-[10px] text-blue-400 hover:underline">View Source</a>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* Metadata */}
                {msg.latency && (
                  <p className="text-[10px] text-gray-600 px-1">
                    Generated in {msg.latency}ms
                  </p>
                )}
              </div>
            </div>
          ))
        )}
        {status && (
          <div className="flex justify-start">
            <div className="text-[10px] uppercase tracking-widest text-brand-500 font-bold animate-pulse">
              {status}
            </div>
          </div>
        )}
      </div>

      {/* Input area */}
      <form onSubmit={handleAsk} className="relative">
        <input
          id="input-ask-query"
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Type your question..."
          className="glass-input !pr-16 !py-4"
          disabled={isStreaming}
        />
        <button
          id="btn-ask-submit"
          type="submit"
          disabled={isStreaming || !query.trim()}
          className="absolute right-2 top-2 bottom-2 aspect-square btn-primary !p-0 !rounded-lg"
        >
          {isStreaming ? (
             <div className="spinner" style={{ width: 16, height: 16, borderWidth: 2 }} />
          ) : (
            '↗️'
          )}
        </button>
      </form>
    </div>
  );
}
