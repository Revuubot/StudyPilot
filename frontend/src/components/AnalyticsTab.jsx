import React, { useState, useEffect } from 'react';
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  BarChart, Bar, Cell
} from 'recharts';
import api from '../api';

/**
 * AnalyticsTab – User performance and system engagement metrics.
 * Shows time saved, trends, and top notes using Recharts.
 */
export default function AnalyticsTab() {
  const [data, setData] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        const [analyticsData, evaluationMetrics] = await Promise.all([
          api.getAnalytics(7),
          api.getMetrics()
        ]);
        setData(analyticsData);
        setMetrics(evaluationMetrics);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchAnalytics();
  }, []);

  if (loading) {
    return (
      <div className="h-96 flex items-center justify-center">
        <div className="spinner" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="glass-card text-center py-20">
        <p className="text-red-400 mb-4">{error}</p>
        <button onClick={() => window.location.reload()} className="btn-primary">Retry</button>
      </div>
    );
  }

  const COLORS = ['#6366f1', '#818cf8', '#4f46e5', '#3730a3', '#1e1b4b'];

  return (
    <div className="space-y-8 animate-fade-in">
      <div>
        <h2 className="section-title">Your Analytics</h2>
        <p className="text-sm text-gray-500 mt-1">Tracking your productivity and study progress</p>
      </div>

      {/* Hero Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="stat-card">
          <div className="stat-value">{data.total_time_saved_minutes.toFixed(0)}</div>
          <div className="stat-label">Min Saved</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{data.total_summaries}</div>
          <div className="stat-label">Summaries</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{data.total_questions}</div>
          <div className="stat-label">Questions</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{data.total_searches}</div>
          <div className="stat-label">Searches</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Trend Chart */}
        <div className="lg:col-span-2 glass-card flex flex-col">
          <h3 className="text-sm font-bold text-white mb-6 uppercase tracking-wider flex items-center gap-2">
            📈 Time Saved Trend (7 Days)
          </h3>
          <div className="flex-1 h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data.daily_trends}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                <XAxis 
                  dataKey="date" 
                  stroke="#4b5563" 
                  fontSize={10} 
                  tickLine={false} 
                  axisLine={false}
                  tickFormatter={(val) => val.split('-').slice(1).join('/')}
                />
                <YAxis stroke="#4b5563" fontSize={10} tickLine={false} axisLine={false} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#0f0f23', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px' }}
                  itemStyle={{ color: '#818cf8', fontSize: '12px' }}
                />
                <Line 
                  type="monotone" 
                  dataKey="time_saved" 
                  stroke="#6366f1" 
                  strokeWidth={3} 
                  dot={{ r: 4, fill: '#6366f1', strokeWidth: 0 }} 
                  activeDot={{ r: 6, fill: '#818cf8' }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Top Notes */}
        <div className="glass-card">
          <h3 className="text-sm font-bold text-white mb-6 uppercase tracking-wider">
            🔥 Most Active Notes
          </h3>
          <div className="space-y-4">
            {data.top_notes.map((note, idx) => (
              <div key={idx} className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-white/[0.03] flex items-center justify-center text-xs font-bold text-brand-400 border border-white/[0.05]">
                  {idx + 1}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-200 truncate">{note.title}</p>
                  <p className="text-[10px] text-gray-500 uppercase">{note.source}</p>
                </div>
                <div className="text-xs font-bold text-white bg-white/[0.05] px-2 py-1 rounded">
                  {note.event_count}
                </div>
              </div>
            ))}
            {data.top_notes.length === 0 && (
              <p className="text-center text-gray-600 py-10 text-sm italic">No activity yet</p>
            )}
          </div>
        </div>
      </div>

      {/* Evaluation Metrics */}
      <div className="glass-card">
        <h3 className="text-sm font-bold text-white mb-6 uppercase tracking-wider flex items-center gap-2">
          🧪 System Performance (RAG Evaluation)
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="space-y-4">
            <div className="flex justify-between items-end">
              <span className="text-xs text-gray-400 uppercase">Avg Retrieval Latency</span>
              <span className="text-sm font-bold text-brand-400">{metrics.avg_retrieval_latency_ms} ms</span>
            </div>
            <div className="w-full h-1.5 bg-white/[0.05] rounded-full overflow-hidden">
              <div className="h-full bg-emerald-500" style={{ width: `${Math.min(100, (500 / metrics.avg_retrieval_latency_ms) * 100)}%` }}></div>
            </div>
          </div>
          <div className="space-y-4">
            <div className="flex justify-between items-end">
              <span className="text-xs text-gray-400 uppercase">Avg Generation Latency</span>
              <span className="text-sm font-bold text-brand-400">{metrics.avg_generation_latency_ms} ms</span>
            </div>
            <div className="w-full h-1.5 bg-white/[0.05] rounded-full overflow-hidden">
              <div className="h-full bg-blue-500" style={{ width: `${Math.min(100, (2000 / metrics.avg_generation_latency_ms) * 100)}%` }}></div>
            </div>
          </div>
          <div className="space-y-4">
            <div className="flex justify-between items-end">
              <span className="text-xs text-gray-400 uppercase">Vector DB Health</span>
              <span className="text-sm font-bold text-brand-400">{metrics.embedding_count} Chunks</span>
            </div>
            <div className="w-full h-1.5 bg-white/[0.05] rounded-full overflow-hidden">
              <div className="h-full bg-purple-500" style={{ width: '100%' }}></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
