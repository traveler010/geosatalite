import { useState, useRef, useCallback } from 'react';
import { ArrowUp, Loader2, Crosshair, Droplets, Fuel, Layers } from 'lucide-react';
import { useAppStore } from '../store/useAppStore';
import { queryBackend } from '../services/api';
import ChatMessage from './ChatMessage';
import TelemetryGrid from './TelemetryGrid';

const QUICK_PROMPTS = [
  { label: 'Detect Aircraft', icon: Crosshair },
  { label: 'Outline Water Bodies', icon: Droplets },
  { label: 'Count Storage Tanks', icon: Fuel },
  { label: 'Identify Land Cover Changes', icon: Layers },
];

export default function SidePanel() {
  const [prompt, setPrompt] = useState('');
  const feedRef = useRef(null);
  const { state, actions } = useAppStore();

  const generateDemoAnalysis = useCallback((query) => {
    const loc = state.activeLocation;
    const isWater = /water|flood|river/i.test(query);
    const isAircraft = /aircraft|runway|plane/i.test(query);

    const color = isWater ? '#38bdf8' : '#facc15';
    const label = isWater ? 'WATER BODY / 92%' : isAircraft ? 'AIRCRAFT / 96%' : 'DETECTED TARGET / 94%';
    const offsets = isWater ? [-0.018, 0.022] : isAircraft ? [-0.014, 0.014, 0.032] : [-0.018, 0.018, 0.035];

    const entities = offsets.map((offset, i) => ({
      lat: loc.latitude + offset * 0.4,
      lng: loc.longitude + offset,
      label: `${label} #${i + 1}`,
      color,
    }));

    actions.setEntities(entities);
  }, [state.activeLocation, actions]);

  const handleSubmit = useCallback(async (e) => {
    e.preventDefault();
    const value = prompt.trim();
    if (!value || state.isQuerying) return;

    actions.addMessage('user', value);
    setPrompt('');
    actions.setQuerying(true);

    try {
      const result = await queryBackend(value, state.activeLocation, state.uploadedFile);
      const responseText = result.response || result.answer || result.message || 'Analysis complete.';

      // Try to extract coordinates from response for entity placement
      const coordMatches = JSON.stringify(result).match(/-?\d+(?:\.\d+)?\s*,\s*-?\d+(?:\.\d+)?/g) || [];
      const coords = coordMatches
        .map(pair => pair.split(',').map(Number))
        .filter(pair => Math.abs(pair[0]) <= 90 && Math.abs(pair[1]) <= 180);

      if (coords.length) {
        actions.setEntities(
          coords.slice(0, 5).map((pair, i) => ({
            lat: pair[0],
            lng: pair[1],
            label: `API TARGET / ${i + 1}`,
            color: '#facc15',
          }))
        );
      }

      actions.addMessage('assistant', responseText, 'LIVE API / 3D ENTITIES UPDATED');
    } catch {
      // Demo fallback
      await new Promise(r => setTimeout(r, 600));
      generateDemoAnalysis(value);

      const isWater = /water|flood|river/i.test(value);
      const responseText = isWater
        ? 'Demo reasoning: I outlined the nearest water body and rendered a cyan 3D marker over the active terrain.'
        : 'Demo reasoning: I located likely targets near the active camera center and rendered glowing 3D analysis markers.';

      actions.addMessage('assistant', responseText, 'DEMO MODE / LOCAL FALLBACK · 3D ENTITIES RENDERED');
    } finally {
      actions.setQuerying(false);
    }
  }, [prompt, state.isQuerying, state.activeLocation, state.uploadedFile, actions, generateDemoAnalysis]);

  const handleQuickPrompt = (label) => {
    setPrompt(label);
  };

  return (
    <aside
      className="glass rounded-[14px] overflow-hidden flex flex-col min-h-[700px] max-md:min-h-[600px]"
      aria-label="AI reasoning and chat console"
    >
      {/* Telemetry */}
      <TelemetryGrid />

      {/* Chat Feed */}
      <div
        ref={feedRef}
        className="flex flex-1 flex-col gap-3.5 min-h-[270px] px-[15px] py-[17px] overflow-y-auto"
        aria-live="polite"
      >
        {state.messages.map((msg) => (
          <ChatMessage
            key={msg.id}
            type={msg.type}
            text={msg.text}
            result={msg.result}
          />
        ))}
      </div>

      {/* Composer */}
      <div className="px-[15px] py-[13px] pt-[13px] pb-[15px] border-t border-border bg-panel-solid">
        <form className="flex gap-2" onSubmit={handleSubmit}>
          <input
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="e.g., Locate aircraft or outline a water body..."
            autoComplete="off"
            className="flex-1 min-w-0 h-[41px] px-3 border border-border-light rounded-lg outline-none bg-panel-input text-text text-[11px] placeholder:text-placeholder focus:border-blue-bright focus:shadow-[0_0_0_3px_rgba(56,189,248,0.12)] transition-all"
          />
          <button
            type="submit"
            disabled={state.isQuerying}
            className="grid place-items-center w-[43px] h-[41px] border border-blue-bright rounded-lg bg-blue text-white text-[17px] hover:bg-blue-hover hover:-translate-y-0.5 transition-all disabled:opacity-65 disabled:cursor-wait"
            aria-label="Send query"
          >
            {state.isQuerying ? (
              <Loader2 className="w-[15px] h-[15px] animate-spin-slow" />
            ) : (
              <ArrowUp className="w-[17px] h-[17px]" />
            )}
          </button>
        </form>

        {/* Quick Prompts */}
        <div className="flex flex-wrap gap-1.5 mt-[9px]">
          {QUICK_PROMPTS.map(({ label, icon: Icon }) => (
            <button
              key={label}
              type="button"
              onClick={() => handleQuickPrompt(label)}
              className="inline-flex items-center gap-1 px-2 py-1.5 border border-border rounded-full bg-transparent text-muted text-[10px] hover:border-emerald hover:text-emerald-light hover:bg-emerald/10 transition-all duration-200"
            >
              <Icon className="w-3 h-3" />
              {label}
            </button>
          ))}
        </div>
      </div>
    </aside>
  );
}
