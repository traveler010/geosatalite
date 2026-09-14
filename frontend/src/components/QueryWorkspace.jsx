import { useState, useCallback, useRef } from 'react';
import { ArrowUp, Loader2, Crosshair, Droplets, Fuel, Layers, Download, Sparkles, Image } from 'lucide-react';
import { useAppStore } from '../store/useAppStore';
import { queryBackendV2, fetchTools } from '../services/api';
import ExecutionTrace from './ExecutionTrace';
import ReportExport from './ReportExport';

const QUICK_PROMPTS = [
  { label: 'Detect aircraft in the image', icon: Crosshair },
  { label: 'Outline water bodies', icon: Droplets },
  { label: 'Count storage tanks', icon: Fuel },
  { label: 'Describe this satellite scene', icon: Sparkles },
  { label: 'Identify land cover changes', icon: Layers },
];

const SAMPLE_QUERIES = [
  "How many buildings are visible?",
  "Is there a water body in this image?",
  "Highlight the runway area",
  "Use the optical and SAR images together to identify built-up and water-covered regions",
  "Has the built-up area increased, decreased, or remained unchanged?",
];

export default function QueryWorkspace() {
  const [prompt, setPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
  const feedRef = useRef(null);
  const { state, actions } = useAppStore();

  const handleSubmit = useCallback(async (e) => {
    e?.preventDefault?.();
    const value = prompt.trim();
    if (!value || loading) return;

    setLoading(true);

    const historyEntry = {
      id: Date.now(),
      query: value,
      timestamp: new Date().toISOString(),
      status: 'pending',
    };
    setHistory(prev => [historyEntry, ...prev]);

    try {
      const queryResult = await queryBackendV2(
        value,
        state.activeLocation,
        state.uploadedPaths || [],
        state.uploadedFile,
      );

      setResult(queryResult);
      historyEntry.status = queryResult.success ? 'success' : 'error';
      historyEntry.result = queryResult;

      setHistory(prev => prev.map(h => h.id === historyEntry.id ? historyEntry : h));

      // Add to chat
      if (queryResult.success) {
        actions.addMessage(
          'assistant',
          queryResult.answer || 'Analysis complete.',
          `${queryResult.task_type?.toUpperCase()} / ${queryResult.tool_used} / ${Math.round((queryResult.confidence || 0) * 100)}% confidence`,
          queryResult.reasoning
        );
      } else {
        actions.addMessage('assistant', queryResult.error || 'Query failed.', 'ERROR');
      }

    } catch (err) {
      historyEntry.status = 'error';
      historyEntry.error = err.message;
      setHistory(prev => prev.map(h => h.id === historyEntry.id ? historyEntry : h));

      // Demo fallback
      const demoResult = {
        query_id: `demo-${Date.now()}`,
        success: true,
        answer: "Demo mode: The system detected 3 potential targets in the analyzed region. In production, this would use RS-adapted specialist models (GeoChat, RemoteCLIP) for accurate inference.",
        confidence: 0.87,
        task_type: 'vqa',
        tool_used: 'rs_vqa_v1 (demo)',
        evidence: {},
        trace: {
          query_id: `demo-${Date.now()}`,
          timestamp: new Date().toISOString(),
          query: value,
          input_summary: { type: 'text_only', modality: 'none', n_images: 0 },
          selected_task: 'vqa',
          selected_tool: 'rs_vqa_v1',
          parameters_used: { question_type: 'scene' },
          confidence: 0.87,
          evidence: {},
          answer: "Demo mode analysis complete.",
          processing_time_ms: 42,
          status: 'success',
        },
        processing_time_ms: 42,
      };
      setResult(demoResult);
      actions.addMessage('assistant', demoResult.answer, 'DEMO MODE / LOCAL FALLBACK');
    } finally {
      setLoading(false);
      setPrompt('');
    }
  }, [prompt, loading, state.activeLocation, state.uploadedPaths, state.uploadedFile, actions]);

  const handleQuickPrompt = (label) => {
    setPrompt(label);
  };

  return (
    <section className="max-w-[1200px] mx-auto">
      <div className="grid grid-cols-[1fr_400px] gap-4 max-lg:grid-cols-1">
        {/* Left: Query Interface */}
        <div className="glass rounded-[14px] overflow-hidden flex flex-col min-h-[700px]">
          {/* Header */}
          <div className="px-5 py-4 border-b border-border bg-panel-solid/95">
            <span className="font-mono text-[10px] tracking-[0.08em] uppercase text-faint">
              Query Workspace
            </span>
            <strong className="block mt-1 text-sm font-bold text-text">
              Natural Language Analysis
            </strong>
            <p className="mt-1 text-[11px] text-muted">
              Ask questions about uploaded imagery. The agentic controller will classify your task,
              select the appropriate specialist model, and return an evidence-grounded answer.
            </p>
          </div>

          {/* Uploaded Images Preview */}
          {state.uploadedPaths?.length > 0 && (
            <div className="px-5 py-3 border-b border-border bg-panel-solid/60">
              <div className="flex items-center gap-2 text-[10px] text-emerald font-mono">
                <Image className="w-3 h-3" />
                {state.uploadedPaths.length} IMAGE(S) LOADED FOR ANALYSIS
              </div>
            </div>
          )}

          {/* Result Display */}
          <div ref={feedRef} className="flex-1 p-5 overflow-y-auto space-y-4">
            {!result && !loading && (
              <div className="flex flex-col items-center justify-center h-full text-center py-16">
                <Sparkles className="w-10 h-10 text-faint mb-4" />
                <p className="text-sm text-text font-medium mb-2">
                  Ready for queries
                </p>
                <p className="text-[11px] text-muted max-w-sm">
                  Enter a natural-language question below or pick a quick prompt.
                  The system will route your query to the appropriate specialist model.
                </p>
                {/* Sample Queries */}
                <div className="mt-5 space-y-1.5 w-full max-w-md">
                  <p className="text-[10px] text-faint font-mono uppercase mb-2">Sample Queries</p>
                  {SAMPLE_QUERIES.map((q) => (
                    <button
                      key={q}
                      onClick={() => setPrompt(q)}
                      className="w-full text-left px-3 py-2 rounded-lg border border-border bg-panel-card text-[11px] text-muted hover:text-text hover:border-blue-bright/30 hover:bg-panel-hover transition-all"
                    >
                      "{q}"
                    </button>
                  ))}
                </div>
              </div>
            )}

            {loading && (
              <div className="flex flex-col items-center justify-center py-16">
                <div className="w-10 h-10 border-2 border-blue-bright/30 border-t-blue-bright rounded-full animate-spin-slow mb-4" />
                <p className="text-sm text-text font-medium">Processing query...</p>
                <p className="text-[11px] text-muted mt-1">
                  Classifying task → Selecting tool → Running inference
                </p>
              </div>
            )}

            {result && !loading && (
              <div className="space-y-4 animate-fade-in">
                {/* Query Echo */}
                <div className="px-4 py-3 rounded-lg border border-gold/20 bg-chat-user-bg">
                  <span className="text-[9px] text-faint font-mono uppercase">Your Query</span>
                  <p className="text-xs text-gold-light mt-1">{result.trace?.query || history[0]?.query}</p>
                </div>

                {/* Answer */}
                <div className="px-4 py-3 rounded-lg border border-border bg-chat-ai-bg">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[9px] text-faint font-mono uppercase">Answer</span>
                    {result.processing_time_ms && (
                      <span className="text-[9px] text-faint font-mono">
                        {result.processing_time_ms} ms
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-text leading-relaxed">{result.answer}</p>

                  {/* Confidence Bar */}
                  {result.confidence != null && (
                    <div className="mt-3 pt-3 border-t border-border">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-[10px] text-muted">Confidence</span>
                        <span className={`text-[12px] font-bold ${
                          result.confidence >= 0.8 ? 'text-emerald' : result.confidence >= 0.55 ? 'text-gold' : 'text-red-400'
                        }`}>
                          {Math.round(result.confidence * 100)}%
                        </span>
                      </div>
                      <div className="h-1.5 bg-border rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all duration-500 ${
                            result.confidence >= 0.8 ? 'bg-emerald' : result.confidence >= 0.55 ? 'bg-gold' : 'bg-red-400'
                          }`}
                          style={{ width: `${Math.round(result.confidence * 100)}%` }}
                        />
                      </div>
                    </div>
                  )}

                  {/* DeepSeek Reasoning Chain of Thought */}
                  {result.reasoning && (
                    <div className="mt-3 pt-3 border-t border-border">
                      <span className="text-[9px] text-blue-bright font-mono uppercase flex items-center gap-1.5">
                        <Sparkles className="w-3 h-3 text-purple-400" />
                        DeepSeek Reasoning (Chain of Thought)
                      </span>
                      <div className="mt-2 p-2.5 rounded bg-bg-deep/80 border border-blue-bright/20 text-[11px] font-mono text-[#a5b4fc] whitespace-pre-wrap leading-relaxed max-h-56 overflow-y-auto">
                        {result.reasoning}
                      </div>
                    </div>
                  )}

                  {/* Bounding Boxes (Grounding Evidence) */}
                  {result.evidence?.bounding_boxes && (
                    <div className="mt-3 pt-3 border-t border-border">
                      <span className="text-[9px] text-faint font-mono uppercase">
                        Detected Regions ({result.evidence.bounding_boxes.length})
                      </span>
                      <div className="mt-2 space-y-1">
                        {result.evidence.bounding_boxes.map((box, i) => (
                          <div key={i} className="flex items-center gap-2 px-2 py-1 rounded bg-bg-deep text-[10px]">
                            <Crosshair className="w-3 h-3 text-blue-bright" />
                            <span className="text-muted">Box {i + 1}:</span>
                            <span className="text-text font-mono">[{box.bbox.join(', ')}]</span>
                            <span className="text-emerald ml-auto">{Math.round(box.confidence * 100)}%</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Class Distribution (Fusion Evidence) */}
                  {result.raw_result?.class_distribution && (
                    <div className="mt-3 pt-3 border-t border-border">
                      <span className="text-[9px] text-faint font-mono uppercase">
                        Land Cover Distribution
                      </span>
                      <div className="mt-2 space-y-1.5">
                        {Object.entries(result.raw_result.class_distribution).map(([cls, pct]) => (
                          <div key={cls} className="flex items-center gap-2">
                            <span className="text-[10px] text-muted w-20 capitalize">{cls.replace('_', ' ')}</span>
                            <div className="flex-1 h-2 bg-border rounded-full overflow-hidden">
                              <div className="h-full bg-blue-bright rounded-full" style={{ width: `${pct}%` }} />
                            </div>
                            <span className="text-[10px] text-text font-mono w-10 text-right">{pct}%</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* Report Export */}
                {result.query_id && (
                  <ReportExport queryId={result.query_id} />
                )}
              </div>
            )}
          </div>

          {/* Composer */}
          <div className="px-5 py-4 border-t border-border bg-panel-solid">
            <form className="flex gap-2" onSubmit={handleSubmit}>
              <input
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="Ask a question about your satellite imagery..."
                autoComplete="off"
                className="flex-1 min-w-0 h-[42px] px-3.5 border border-border-light rounded-lg outline-none bg-panel-input text-text text-xs placeholder:text-placeholder focus:border-blue-bright focus:shadow-[0_0_0_3px_rgba(56,189,248,0.12)] transition-all"
              />
              <button
                type="submit"
                disabled={loading || !prompt.trim()}
                className="grid place-items-center w-[44px] h-[42px] border border-blue-bright rounded-lg bg-blue text-white hover:bg-blue-hover hover:-translate-y-0.5 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                aria-label="Send query"
              >
                {loading ? (
                  <Loader2 className="w-4 h-4 animate-spin-slow" />
                ) : (
                  <ArrowUp className="w-[18px] h-[18px]" />
                )}
              </button>
            </form>

            {/* Quick Prompts */}
            <div className="flex flex-wrap gap-1.5 mt-3">
              {QUICK_PROMPTS.map(({ label, icon: Icon }) => (
                <button
                  key={label}
                  type="button"
                  onClick={() => handleQuickPrompt(label)}
                  className="inline-flex items-center gap-1 px-2.5 py-1.5 border border-border rounded-full bg-transparent text-muted text-[10px] hover:border-emerald hover:text-emerald-light hover:bg-emerald/10 transition-all duration-200"
                >
                  <Icon className="w-3 h-3" />
                  {label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Right: Execution Trace & History */}
        <div className="flex flex-col gap-4">
          {/* Trace Panel */}
          {result?.trace && (
            <ExecutionTrace trace={result.trace} />
          )}

          {/* Query History */}
          {history.length > 0 && (
            <div className="glass rounded-[14px] overflow-hidden">
              <div className="px-4 py-3 border-b border-border bg-panel-solid/95">
                <span className="font-mono text-[10px] tracking-[0.08em] uppercase text-muted">
                  Query History
                </span>
              </div>
              <div className="p-3 space-y-2 max-h-[300px] overflow-y-auto">
                {history.map((entry) => (
                  <div
                    key={entry.id}
                    className="px-3 py-2 rounded-lg border border-border bg-panel-card cursor-pointer hover:border-blue-bright/30 transition-colors"
                    onClick={() => {
                      if (entry.result) setResult(entry.result);
                    }}
                  >
                    <p className="text-[11px] text-text truncate">{entry.query}</p>
                    <div className="flex items-center gap-2 mt-1">
                      <span className={`w-1.5 h-1.5 rounded-full ${
                        entry.status === 'success' ? 'bg-emerald' :
                        entry.status === 'error' ? 'bg-red-400' : 'bg-gold'
                      }`} />
                      <span className="text-[9px] text-faint font-mono">
                        {new Date(entry.timestamp).toLocaleTimeString()}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
