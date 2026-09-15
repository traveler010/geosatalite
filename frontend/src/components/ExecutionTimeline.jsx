import { useState } from 'react';
import {
  Clock,
  Cpu,
  Target,
  CheckCircle2,
  AlertCircle,
  ChevronDown,
  ChevronRight,
  Layers,
  Database,
  BarChart3,
  Bot,
  Activity,
  Zap,
} from 'lucide-react';

const STEP_ICONS = {
  1: Layers,
  2: Bot,
  3: Cpu,
  4: BarChart3,
  5: Database,
};

export default function ExecutionTimeline({ trace, executionSteps }) {
  const [expandedStep, setExpandedStep] = useState(null);

  const steps = executionSteps || trace?.execution_steps || [
    {
      step: 1,
      name: 'Input Georeferencing & Modality Check',
      tool: 'input_checker',
      status: 'completed',
      duration_ms: Math.round((trace?.processing_time_ms || 80) * 0.12),
      details: `Format: ${trace?.input_summary?.format || 'GeoTIFF'} | Modality: ${trace?.input_summary?.modality || 'optical'}`,
    },
    {
      step: 2,
      name: 'Agent Planning & Tool Routing',
      tool: 'agent_planner',
      status: 'completed',
      duration_ms: Math.round((trace?.processing_time_ms || 80) * 0.08),
      details: `Routed task '${trace?.selected_task || 'analysis'}' to '${trace?.selected_tool || 'specialist'}'`,
    },
    {
      step: 3,
      name: 'Specialist Neural Inference',
      tool: trace?.selected_tool || 'specialist_model',
      status: trace?.status === 'error' ? 'error' : 'completed',
      duration_ms: Math.round((trace?.processing_time_ms || 80) * 0.60),
      details: `Model confidence: ${Math.round((trace?.confidence || 0.9) * 100)}%`,
    },
    {
      step: 4,
      name: 'Evidence Aggregation & XAI',
      tool: 'aggregator',
      status: 'completed',
      duration_ms: Math.round((trace?.processing_time_ms || 80) * 0.15),
      details: 'Extracted radiometric metrics, spectral indices, and spatial evidence',
    },
    {
      step: 5,
      name: 'Trace & Report Indexing',
      tool: 'session_service',
      status: 'completed',
      duration_ms: Math.round((trace?.processing_time_ms || 80) * 0.05),
      details: 'Persisted auditable execution trace and indexed downloadable report',
    },
  ];

  const totalTime = trace?.processing_time_ms || steps.reduce((sum, s) => sum + (s.duration_ms || 0), 0) || 100;

  const toggleStep = (idx) => {
    setExpandedStep(expandedStep === idx ? null : idx);
  };

  return (
    <div className="rounded-xl border border-border bg-panel-card p-4 space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border/70 pb-2.5">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-blue-bright" />
          <span className="font-mono text-[10px] tracking-[0.08em] uppercase text-text font-bold">
            Execution Pipeline Timeline
          </span>
          <span className="px-1.5 py-0.5 rounded text-[9px] font-mono bg-blue/15 text-blue-bright border border-blue/30 font-semibold">
            {steps.length} STAGES
          </span>
        </div>
        <div className="flex items-center gap-1.5 text-[10px] font-mono text-muted">
          <Clock className="w-3.5 h-3.5 text-faint" />
          <span>{totalTime} ms total</span>
        </div>
      </div>

      {/* Stepper Timeline */}
      <div className="relative pl-6 space-y-3 mt-2 before:content-[''] before:absolute before:left-[11px] before:top-2 before:bottom-2 before:w-[2px] before:bg-gradient-to-b before:from-blue-bright/60 before:via-emerald/60 before:to-border">
        {steps.map((step, idx) => {
          const StepIcon = STEP_ICONS[step.step] || Zap;
          const isCompleted = step.status === 'completed' || step.status === 'success' || !step.status;
          const isError = step.status === 'error';
          const pct = Math.min(100, Math.max(8, Math.round(((step.duration_ms || 10) / Math.max(totalTime, 1)) * 100)));
          const isExpanded = expandedStep === idx;

          return (
            <div key={idx} className="relative group">
              {/* Step Marker Node */}
              <div
                className={`absolute -left-6 top-1 w-5 h-5 rounded-full flex items-center justify-center border text-[9px] font-mono font-bold transition-all shadow-sm ${
                  isError
                    ? 'bg-red-500/20 border-red-500 text-red-400 shadow-red-500/20'
                    : isCompleted
                    ? 'bg-emerald/20 border-emerald text-emerald-light shadow-emerald/20'
                    : 'bg-blue/20 border-blue-bright text-blue-bright shadow-blue/20'
                }`}
              >
                {step.step || idx + 1}
              </div>

              {/* Step Card */}
              <div
                onClick={() => toggleStep(idx)}
                className={`rounded-lg border px-3 py-2.5 cursor-pointer transition-all ${
                  isExpanded
                    ? 'border-blue-bright/40 bg-panel-hover shadow-[0_0_12px_rgba(56,189,248,0.1)]'
                    : 'border-border/80 bg-bg-deep/60 hover:border-border-light hover:bg-panel-hover/50'
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2 min-w-0">
                    <StepIcon className="w-3.5 h-3.5 text-blue-bright shrink-0" />
                    <span className="text-xs font-semibold text-text truncate">
                      {step.name}
                    </span>
                    <span className="px-1.5 py-0.5 rounded-full text-[9px] font-mono bg-panel-card border border-border text-muted">
                      {step.tool}
                    </span>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    <span className="text-[10px] font-mono text-muted">
                      {step.duration_ms} ms
                    </span>
                    {isError ? (
                      <AlertCircle className="w-3.5 h-3.5 text-red-400" />
                    ) : (
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald" />
                    )}
                    {isExpanded ? (
                      <ChevronDown className="w-3 h-3 text-faint" />
                    ) : (
                      <ChevronRight className="w-3 h-3 text-faint" />
                    )}
                  </div>
                </div>

                {/* Progress Bar of Time Contribution */}
                <div className="mt-2 h-1 bg-border/80 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${
                      isError ? 'bg-red-400' : 'bg-gradient-to-r from-blue-bright to-emerald'
                    }`}
                    style={{ width: `${pct}%` }}
                  />
                </div>

                {/* Expanded Details */}
                {isExpanded && step.details && (
                  <div className="mt-2.5 pt-2 border-t border-border/50 text-[11px] font-mono text-muted leading-relaxed">
                    <span className="text-faint text-[9px] uppercase tracking-wider block mb-0.5">Stage Metadata:</span>
                    <p className="text-[#a5b4fc]">{step.details}</p>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
