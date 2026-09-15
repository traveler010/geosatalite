import { useState } from 'react';
import { useAppStore } from '../store/useAppStore';
import { formatCoordinate } from '../services/api';
import {
  Crosshair,
  Calendar,
  Layers,
  Database,
  Compass,
  CheckCircle2,
  X,
  Copy,
  Check,
  Radio,
} from 'lucide-react';

/**
 * Phase 4 Futuristic Location Card
 * Displays comprehensive spatial, sensor, and acquisition intelligence
 * with cyber glassmorphic aesthetics.
 */
export default function LocationCard() {
  const { state, actions } = useAppStore();
  const { locationCard, globeState } = state;
  const [copied, setCopied] = useState(false);

  if (!locationCard || !locationCard.visible) {
    return null;
  }

  const handleCopy = () => {
    const text = `${locationCard.latitude.toFixed(6)}, ${locationCard.longitude.toFixed(6)}`;
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleFocus = () => {
    actions.flyTo(
      {
        latitude: locationCard.latitude,
        longitude: locationCard.longitude,
        altitude: locationCard.altitude || 3000,
      },
      locationCard.location
    );
  };

  // State badge styling
  const stateBadge = {
    idle: { label: 'STANDBY', color: 'text-slate-400 bg-slate-800/80 border-slate-700' },
    processing: { label: 'SCANNING AOI', color: 'text-amber-400 bg-amber-950/80 border-amber-800' },
    location_found: { label: 'LOCATION ACQUIRED', color: 'text-emerald-400 bg-emerald-950/80 border-emerald-800' },
    location_locked: { label: 'TARGET LOCKED', color: 'text-cyan-400 bg-cyan-950/80 border-cyan-700 shadow-[0_0_12px_rgba(6,182,212,0.3)]' },
    location_unknown: { label: 'UNRESOLVED', color: 'text-rose-400 bg-rose-950/80 border-rose-800' },
  }[globeState] || { label: 'ACTIVE TARGET', color: 'text-cyan-400 bg-cyan-950/80 border-cyan-800' };

  return (
    <aside
      className="absolute bottom-12 right-4 z-20 w-[340px] max-sm:w-[calc(100%-2rem)] max-sm:right-4 backdrop-blur-xl bg-[#08101ee6] border border-cyan-500/30 rounded-xl shadow-[0_12px_40px_rgba(0,0,0,0.6)] text-text overflow-hidden transition-all duration-300 animate-in fade-in slide-in-from-bottom-4"
      aria-label="Target Location Card"
    >
      {/* Top Cyber Accent Bar */}
      <div className="h-[2px] w-full bg-gradient-to-r from-transparent via-cyan-400 to-transparent animate-pulse" />

      {/* Header */}
      <div className="p-3.5 pb-2.5 flex items-start justify-between gap-2 border-b border-border/60">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span
              className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full font-mono text-[9px] font-semibold tracking-wider border ${stateBadge.color}`}
            >
              <Radio className="w-2.5 h-2.5 animate-pulse" />
              {stateBadge.label}
            </span>
            <span className="font-mono text-[9px] text-faint">
              CONF: {Math.round((locationCard.confidence || 0.95) * 100)}%
            </span>
          </div>
          <h4 className="text-sm font-bold text-white tracking-tight line-clamp-1">
            {locationCard.location || 'Target Region'}
          </h4>
        </div>

        <button
          onClick={actions.hideLocationCard}
          className="p-1 rounded-md text-faint hover:text-white hover:bg-panel-hover transition-colors"
          title="Close Card"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Coordinates Badge */}
      <div className="mx-3.5 mt-2.5 p-2 rounded-lg bg-bg-deep/80 border border-border/80 flex items-center justify-between font-mono text-[11px]">
        <div className="flex items-center gap-1.5 text-cyan-300">
          <Compass className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
          <span>
            {formatCoordinate(locationCard.latitude, 'N', 'S')},{' '}
            {formatCoordinate(locationCard.longitude, 'E', 'W')}
          </span>
        </div>
        <button
          onClick={handleCopy}
          className="p-1 rounded text-faint hover:text-cyan-300 hover:bg-cyan-950/40 transition-colors"
          title="Copy Decimal Coordinates"
        >
          {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
        </button>
      </div>

      {/* Metadata Grid */}
      <div className="p-3.5 pt-2.5 grid grid-cols-2 gap-2 text-[10px] font-mono">
        <div className="p-2 rounded-lg bg-panel-solid/40 border border-border/40">
          <span className="flex items-center gap-1 text-faint mb-0.5">
            <Layers className="w-3 h-3 text-cyan-400" />
            SENSOR
          </span>
          <strong className="text-white font-medium block truncate">
            {locationCard.sensor || 'Sentinel-2 MSI'}
          </strong>
        </div>

        <div className="p-2 rounded-lg bg-panel-solid/40 border border-border/40">
          <span className="flex items-center gap-1 text-faint mb-0.5">
            <Database className="w-3 h-3 text-emerald-400" />
            SOURCE
          </span>
          <strong className="text-white font-medium block truncate">
            {locationCard.source || 'Copernicus / Scene'}
          </strong>
        </div>

        <div className="p-2 rounded-lg bg-panel-solid/40 border border-border/40">
          <span className="flex items-center gap-1 text-faint mb-0.5">
            <Calendar className="w-3 h-3 text-amber-400" />
            ACQUIRED
          </span>
          <strong className="text-white font-medium block truncate">
            {locationCard.acquisitionDate || '2026-09-14'}
          </strong>
        </div>

        <div className="p-2 rounded-lg bg-panel-solid/40 border border-border/40">
          <span className="flex items-center gap-1 text-faint mb-0.5">
            <CheckCircle2 className="w-3 h-3 text-purple-400" />
            GSD / RES
          </span>
          <strong className="text-white font-medium block truncate">
            {locationCard.resolution || '10m Optical'}
          </strong>
        </div>
      </div>

      {/* Actions Footer */}
      <div className="px-3.5 pb-3 flex items-center gap-2">
        <button
          onClick={handleFocus}
          className="flex-1 py-1.5 px-3 rounded-lg bg-cyan-600/20 hover:bg-cyan-600/30 border border-cyan-500/40 text-cyan-200 text-[11px] font-mono font-medium flex items-center justify-center gap-1.5 transition-all shadow-[0_0_12px_rgba(6,182,212,0.15)]"
        >
          <Crosshair className="w-3.5 h-3.5" />
          Focus Optical Camera
        </button>
      </div>
    </aside>
  );
}
