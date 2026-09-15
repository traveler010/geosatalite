import { useState, useCallback } from 'react';
import { ChevronDown, ChevronRight, Copy, Check, Clock, Cpu, Target, Gauge, FileJson } from 'lucide-react';
import ExecutionTimeline from './ExecutionTimeline';

export default function ExecutionTrace({ trace }) {
  const [expanded, setExpanded] = useState(true);
  const [jsonExpanded, setJsonExpanded] = useState(false);
  const [copied, setCopied] = useState(false);

  const copyTrace = useCallback(() => {
    navigator.clipboard.writeText(JSON.stringify(trace, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [trace]);

  if (!trace) return null;

  const confidence = trace.confidence || 0;
  const confPct = Math.round(confidence * 100);
  const confColor = confidence >= 0.8 ? 'text-emerald' : confidence >= 0.55 ? 'text-gold' : 'text-red-400';
  const confBg = confidence >= 0.8 ? 'bg-emerald' : confidence >= 0.55 ? 'bg-gold' : 'bg-red-400';

  return (
    <div className="glass rounded-[12px] overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-4 py-3 bg-panel-solid/95 border-b border-border hover:bg-panel-hover transition-colors"
      >
        <div className="flex items-center gap-2">
          <FileJson className="w-4 h-4 text-blue-bright" />
          <span className="font-mono text-[10px] tracking-[0.08em] uppercase text-muted">
            Execution Trace
          </span>
          <span className={`px-1.5 py-0.5 rounded text-[9px] font-mono font-semibold ${
            trace.status === 'success'
              ? 'bg-emerald/15 text-emerald-light border border-emerald/30'
              : 'bg-red-500/15 text-red-300 border border-red-500/30'
          }`}>
            {trace.status?.toUpperCase()}
          </span>
        </div>
        {expanded ? <ChevronDown className="w-4 h-4 text-muted" /> : <ChevronRight className="w-4 h-4 text-muted" />}
      </button>

      {expanded && (
        <div className="p-4 space-y-3">
          {/* Summary Row */}
          <div className="grid grid-cols-2 gap-2 max-sm:grid-cols-1">
            <TraceField icon={Target} label="Task" value={trace.selected_task} highlight />
            <TraceField icon={Cpu} label="Tool" value={trace.selected_tool} />
            <TraceField icon={Clock} label="Time" value={`${trace.processing_time_ms} ms`} />
            <div className="flex items-center gap-2 px-3 py-2 rounded-lg border border-border bg-panel-card">
              <Gauge className="w-3.5 h-3.5 text-faint shrink-0" />
              <div className="flex-1 min-w-0">
                <span className="text-[9px] text-faint font-mono uppercase">Confidence</span>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className={`text-[13px] font-bold ${confColor}`}>{confPct}%</span>
                  <div className="flex-1 h-1.5 bg-border rounded-full overflow-hidden">
                    <div className={`h-full ${confBg} rounded-full transition-all`} style={{ width: `${confPct}%` }} />
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Parameters */}
          {trace.parameters_used && Object.keys(trace.parameters_used).length > 0 && (
            <div className="px-3 py-2.5 rounded-lg border border-border bg-panel-card">
              <span className="text-[9px] text-faint font-mono uppercase">Parameters Used</span>
              <div className="flex flex-wrap gap-1.5 mt-1.5">
                {Object.entries(trace.parameters_used).map(([k, v]) => (
                  <span key={k} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-bg-deep border border-border text-[10px] text-muted">
                    <span className="text-blue-bright">{k}:</span>
                    <span className="text-text">{Array.isArray(v) ? v.join(', ') : String(v)}</span>
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Evidence */}
          {trace.evidence && Object.keys(trace.evidence).length > 0 && (
            <div className="px-3 py-2.5 rounded-lg border border-border bg-panel-card">
              <span className="text-[9px] text-faint font-mono uppercase">Evidence</span>
              <div className="mt-1.5 space-y-1">
                {Object.entries(trace.evidence).map(([k, v]) => {
                  const display = typeof v === 'object' ? JSON.stringify(v) : String(v);
                  return (
                    <div key={k} className="flex gap-2 text-[10px]">
                      <span className="text-muted shrink-0">{k}:</span>
                      <span className="text-text break-all">{display}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Input Summary */}
          {trace.input_summary && (
            <div className="px-3 py-2.5 rounded-lg border border-border bg-panel-card">
              <span className="text-[9px] text-faint font-mono uppercase">Input Summary</span>
              <div className="flex flex-wrap gap-1.5 mt-1.5">
                {Object.entries(trace.input_summary).map(([k, v]) => (
                  <span key={k} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-bg-deep border border-border text-[10px] text-muted">
                    <span className="text-emerald">{k}:</span>
                    <span className="text-text">{String(v)}</span>
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Interactive Stepper Timeline */}
          <ExecutionTimeline trace={trace} executionSteps={trace.execution_steps} />

          {/* Full JSON Toggle */}
          <div>
            <button
              onClick={() => setJsonExpanded(!jsonExpanded)}
              className="flex items-center gap-1.5 text-[10px] text-muted hover:text-blue-bright transition-colors"
            >
              {jsonExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
              Full JSON Trace
            </button>

            {jsonExpanded && (
              <div className="relative mt-2">
                <button
                  onClick={copyTrace}
                  className="absolute top-2 right-2 p-1.5 rounded-md bg-panel-hover border border-border text-muted hover:text-text transition-colors z-10"
                  title="Copy JSON"
                >
                  {copied ? <Check className="w-3 h-3 text-emerald" /> : <Copy className="w-3 h-3" />}
                </button>
                <pre className="p-3 rounded-lg bg-bg-deep border border-border text-[10px] font-mono text-muted overflow-x-auto whitespace-pre-wrap max-h-[300px] overflow-y-auto">
                  {JSON.stringify(trace, null, 2)}
                </pre>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function TraceField({ icon: Icon, label, value, highlight = false }) {
  return (
    <div className="flex items-center gap-2 px-3 py-2 rounded-lg border border-border bg-panel-card">
      <Icon className="w-3.5 h-3.5 text-faint shrink-0" />
      <div className="flex-1 min-w-0">
        <span className="text-[9px] text-faint font-mono uppercase">{label}</span>
        <p className={`text-[11px] font-medium truncate ${highlight ? 'text-blue-bright' : 'text-text'}`}>
          {value || 'N/A'}
        </p>
      </div>
    </div>
  );
}
