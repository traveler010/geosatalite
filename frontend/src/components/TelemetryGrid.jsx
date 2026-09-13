import { useAppStore } from '../store/useAppStore';
import { Activity } from 'lucide-react';

export default function TelemetryGrid() {
  const { state } = useAppStore();

  const metrics = [
    { label: 'Camera Altitude', value: state.cameraAltitude, className: 'text-blue-bright' },
    { label: 'Active Center', value: state.cameraCenter, className: 'text-text' },
    { label: 'Ground Sampling Distance', value: '0.5m / pixel', className: 'text-text' },
    { label: 'Sensor Modality', value: state.modality, className: 'text-text' },
  ];

  return (
    <div className="p-[15px] border-b border-border bg-panel-solid">
      {/* Section Title */}
      <div className="flex justify-between mb-[11px] font-mono text-[10px] tracking-[0.1em] uppercase">
        <span className="flex items-center gap-1.5 text-muted">
          <Activity className="w-3 h-3" />
          Live Telemetry HUD
        </span>
        <span className="flex items-center gap-1 text-emerald-dim">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald animate-pulse-glow" />
          STREAMING
        </span>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-2 gap-2 max-sm:grid-cols-1">
        {metrics.map((metric) => (
          <div
            key={metric.label}
            className="min-w-0 px-[11px] py-[10px] border border-border rounded-lg bg-panel-card"
          >
            <small className="block font-mono text-[9px] uppercase text-faint">
              {metric.label}
            </small>
            <strong
              className={`block mt-1 text-[11px] overflow-hidden text-ellipsis whitespace-nowrap ${metric.className}`}
            >
              {metric.value}
            </strong>
          </div>
        ))}
      </div>
    </div>
  );
}
