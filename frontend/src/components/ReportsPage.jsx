import { useState, useEffect, useCallback } from 'react';
import { FileText, Clock, Target, Gauge, Trash2, RefreshCw, ExternalLink, Download } from 'lucide-react';
import ReportExport from './ReportExport';
import ExecutionTimeline from './ExecutionTimeline';
import { BACKEND_BASE } from '../services/api';


export default function ReportsPage() {
  const [traces, setTraces] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedTrace, setSelectedTrace] = useState(null);

  const fetchTraces = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${BACKEND_BASE}/api/traces`);
      if (res.ok) {
        const data = await res.json();
        setTraces(data.traces || []);
      }
    } catch {
      // Backend unavailable — show empty state
      setTraces([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTraces();
  }, [fetchTraces]);

  const confColor = (c) => c >= 0.8 ? 'text-emerald' : c >= 0.55 ? 'text-gold' : 'text-red-400';

  return (
    <section className="max-w-[1200px] mx-auto">
      <div className="glass rounded-[14px] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-border bg-panel-solid/95">
          <div>
            <span className="font-mono text-[10px] tracking-[0.08em] uppercase text-faint">
              Analysis Reports
            </span>
            <strong className="block mt-1 text-sm font-bold text-text">
              Query History & Reports
            </strong>
            <p className="mt-1 text-[11px] text-muted">
              View past queries, execution traces, and download reports.
            </p>
          </div>
          <button
            onClick={fetchTraces}
            disabled={loading}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-border text-[11px] text-muted hover:text-text hover:border-blue-bright/40 hover:bg-panel-hover transition-all disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin-slow' : ''}`} />
            Refresh
          </button>
        </div>

        {/* Content */}
        <div className="p-5">
          {traces.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <FileText className="w-10 h-10 text-faint mb-4" />
              <p className="text-sm text-text font-medium mb-2">No reports yet</p>
              <p className="text-[11px] text-muted max-w-sm">
                {loading ? 'Loading...' : 'Run queries in the Query Workspace to generate analysis reports and execution traces.'}
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-[1fr_1fr] gap-4 max-lg:grid-cols-1">
              {/* Trace List */}
              <div className="space-y-2 max-h-[600px] overflow-y-auto pr-2">
                {traces.map((trace) => (
                  <div
                    key={trace.query_id}
                    onClick={() => setSelectedTrace(trace)}
                    className={`px-4 py-3 rounded-lg border cursor-pointer transition-all ${
                      selectedTrace?.query_id === trace.query_id
                        ? 'border-blue-bright/50 bg-blue/10'
                        : 'border-border bg-panel-card hover:border-blue-bright/30 hover:bg-panel-hover'
                    }`}
                  >
                    <p className="text-xs text-text font-medium truncate">{trace.query}</p>
                    <div className="flex items-center gap-3 mt-2 flex-wrap">
                      <span className="inline-flex items-center gap-1 text-[10px] text-muted">
                        <Target className="w-3 h-3" />
                        {trace.selected_task || 'N/A'}
                      </span>
                      <span className={`inline-flex items-center gap-1 text-[10px] ${confColor(trace.confidence)}`}>
                        <Gauge className="w-3 h-3" />
                        {Math.round((trace.confidence || 0) * 100)}%
                      </span>
                      <span className="inline-flex items-center gap-1 text-[10px] text-muted">
                        <Clock className="w-3 h-3" />
                        {trace.processing_time_ms}ms
                      </span>
                      <span className={`ml-auto px-1.5 py-0.5 rounded text-[9px] font-mono ${
                        trace.status === 'success'
                          ? 'bg-emerald/15 text-emerald-light'
                          : 'bg-red-500/15 text-red-300'
                      }`}>
                        {trace.status}
                      </span>
                    </div>
                  </div>
                ))}
              </div>

              {/* Selected Trace Detail */}
              <div className="glass-readout rounded-lg p-4 min-h-[400px]">
                {selectedTrace ? (
                  <div className="space-y-3">
                    <div>
                      <span className="text-[9px] text-faint font-mono uppercase">Query</span>
                      <p className="text-xs text-text mt-1">{selectedTrace.query}</p>
                    </div>

                    <div>
                      <span className="text-[9px] text-faint font-mono uppercase">Answer</span>
                      <p className="text-xs text-text mt-1 leading-relaxed">{selectedTrace.answer || 'N/A'}</p>
                    </div>

                    <div className="grid grid-cols-2 gap-2">
                      <div className="px-3 py-2 rounded-lg border border-border bg-panel-card">
                        <span className="text-[9px] text-faint font-mono uppercase">Task</span>
                        <p className="text-[11px] text-blue-bright font-medium mt-0.5">{selectedTrace.selected_task}</p>
                      </div>
                      <div className="px-3 py-2 rounded-lg border border-border bg-panel-card">
                        <span className="text-[9px] text-faint font-mono uppercase">Tool</span>
                        <p className="text-[11px] text-text font-medium mt-0.5">{selectedTrace.selected_tool}</p>
                      </div>
                      <div className="px-3 py-2 rounded-lg border border-border bg-panel-card">
                        <span className="text-[9px] text-faint font-mono uppercase">Confidence</span>
                        <p className={`text-[11px] font-bold mt-0.5 ${confColor(selectedTrace.confidence)}`}>
                          {Math.round((selectedTrace.confidence || 0) * 100)}%
                        </p>
                      </div>
                      <div className="px-3 py-2 rounded-lg border border-border bg-panel-card">
                        <span className="text-[9px] text-faint font-mono uppercase">Time</span>
                        <p className="text-[11px] text-text font-medium mt-0.5">{selectedTrace.processing_time_ms}ms</p>
                      </div>
                    </div>

                    {/* Full JSON */}
                    <div>
                      <span className="text-[9px] text-faint font-mono uppercase">Full Trace</span>
                      <pre className="mt-1 p-3 rounded-lg bg-bg-deep border border-border text-[9px] font-mono text-muted overflow-x-auto whitespace-pre-wrap max-h-[200px] overflow-y-auto">
                        {JSON.stringify(selectedTrace, null, 2)}
                      </pre>
                    </div>

                    {/* Execution Timeline */}
                    <ExecutionTimeline trace={selectedTrace} executionSteps={selectedTrace.execution_steps} />

                    {/* Download */}
                    <ReportExport queryId={selectedTrace.query_id} />
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center h-full text-center">
                    <FileText className="w-8 h-8 text-faint mb-3" />
                    <p className="text-xs text-muted">Select a trace to view details</p>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
