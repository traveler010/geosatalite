import { useState, useEffect, useMemo, useCallback } from 'react';
import { useAppStore } from '../store/useAppStore';
import { getSolarConditionAtLocation, calculateSolarPosition } from '../utils/solarCalculator';
import { Sun, Moon, Sunrise, Sunset, Play, Pause, RotateCcw, Clock, Sparkles } from 'lucide-react';

export default function SolarTimeHUD() {
  const { state, actions } = useAppStore();
  const [liveDate, setLiveDate] = useState(new Date());

  // Update live clock every second
  useEffect(() => {
    const interval = setInterval(() => {
      setLiveDate(new Date());
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  // Compute effective date based on live vs manual scrub
  const effectiveDate = useMemo(() => {
    if (state.timeMode === 'live') {
      return liveDate;
    }
    const d = new Date(liveDate);
    const totalMinutes = state.customUtcHours * 60;
    const hours = Math.floor(totalMinutes / 60) % 24;
    const minutes = Math.floor(totalMinutes % 60);
    const seconds = Math.floor((totalMinutes * 60) % 60);
    d.setUTCHours(hours, minutes, seconds, 0);
    return d;
  }, [state.timeMode, liveDate, state.customUtcHours]);

  // Compute active location solar condition
  const activeCondition = useMemo(() => {
    return getSolarConditionAtLocation(
      state.activeLocation.latitude,
      state.activeLocation.longitude,
      effectiveDate
    );
  }, [state.activeLocation, effectiveDate]);

  // Time-lapse loop
  useEffect(() => {
    if (!state.isPlayingTimelapse) return;
    const timer = setInterval(() => {
      actions.setCustomUtcHours((prev) => {
        const next = (prev + 0.1) % 24;
        return Math.round(next * 100) / 100;
      });
    }, 80);
    return () => clearInterval(timer);
  }, [state.isPlayingTimelapse, actions]);

  const handleSliderChange = (e) => {
    if (state.timeMode === 'live') {
      actions.setTimeMode('manual');
    }
    actions.setCustomUtcHours(parseFloat(e.target.value));
  };

  const handleSetPreset = (utcHours) => {
    actions.setTimeMode('manual');
    actions.setCustomUtcHours(utcHours);
  };

  const handleResetLive = () => {
    actions.setTimeMode('live');
    const now = new Date();
    actions.setCustomUtcHours(now.getUTCHours() + now.getUTCMinutes() / 60);
  };

  // Format UTC string
  const utcHours = effectiveDate.getUTCHours();
  const utcMins = effectiveDate.getUTCMinutes();
  const utcStr = `${String(utcHours).padStart(2, '0')}:${String(utcMins).padStart(2, '0')} UTC`;

  // Format IST (+5:30) string
  const istDate = new Date(effectiveDate.getTime() + (5.5 * 3600 * 1000));
  const istStr = `${String(istDate.getUTCHours()).padStart(2, '0')}:${String(istDate.getUTCMinutes()).padStart(2, '0')} IST`;

  const sliderValue = state.timeMode === 'live'
    ? effectiveDate.getUTCHours() + effectiveDate.getUTCMinutes() / 60
    : state.customUtcHours;

  return (
    <div className="absolute bottom-3 left-3 right-3 z-10 pointer-events-auto">
      <div className="glass px-3.5 py-2.5 rounded-xl border border-border/80 bg-bg-deep/90 backdrop-blur-md shadow-2xl flex flex-col gap-2">
        {/* Top Row: Indicators and Quick Presets */}
        <div className="flex items-center justify-between gap-2 max-sm:flex-wrap">
          {/* Active Location Day/Night Status Badge */}
          <div className="flex items-center gap-2">
            <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-mono font-medium border ${
              activeCondition.phase === 'day'
                ? 'bg-amber-500/15 border-amber-500/30 text-amber-300'
                : activeCondition.phase === 'twilight' || activeCondition.phase === 'nautical_twilight'
                ? 'bg-orange-500/15 border-orange-500/30 text-orange-300'
                : 'bg-indigo-500/20 border-indigo-500/40 text-cyan-300 shadow-[0_0_10px_rgba(56,189,248,0.15)]'
            }`}>
              {activeCondition.phase === 'day' ? (
                <>
                  <Sun className="w-3.5 h-3.5 text-amber-400 animate-spin-slow" />
                  <span>DAYLIGHT ({activeCondition.altitudeDeg > 0 ? `+${activeCondition.altitudeDeg}°` : `${activeCondition.altitudeDeg}°`})</span>
                </>
              ) : activeCondition.phase === 'twilight' || activeCondition.phase === 'nautical_twilight' ? (
                <>
                  <Sunrise className="w-3.5 h-3.5 text-orange-400" />
                  <span>TWILIGHT ({activeCondition.altitudeDeg}°)</span>
                </>
              ) : (
                <>
                  <Moon className="w-3.5 h-3.5 text-cyan-400 animate-pulse" />
                  <span>NIGHT MODE · CITY LIGHTS ON</span>
                </>
              )}
            </div>

            <span className="text-[10px] font-mono text-muted hidden md:inline-block">
              Target Solar Time: <strong className="text-text">{activeCondition.solarTimeStr}</strong>
            </span>
          </div>

          {/* Time Readout: UTC & IST */}
          <div className="flex items-center gap-2 font-mono text-[11px]">
            <div className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-panel-solid/90 border border-border text-text">
              <Clock className="w-3 h-3 text-emerald" />
              <span>{utcStr}</span>
              <span className="text-muted">/</span>
              <span className="text-emerald-light">{istStr}</span>
            </div>

            {/* Live Indicator */}
            {state.timeMode === 'live' ? (
              <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-emerald/15 border border-emerald/30 text-emerald text-[9px] uppercase font-bold tracking-wider animate-pulse">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald"></span>
                LIVE
              </span>
            ) : (
              <button
                onClick={handleResetLive}
                className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-blue-500/20 border border-blue-400/30 text-blue-300 text-[10px] hover:bg-blue-500/30 transition-colors cursor-pointer"
                title="Sync back to current real-world time"
              >
                <RotateCcw className="w-2.5 h-2.5" />
                Sync Live
              </button>
            )}
          </div>
        </div>

        {/* Bottom Row: 24h Slider & Quick Jump Controls */}
        <div className="flex items-center gap-3">
          {/* Play/Pause Timelapse */}
          <button
            onClick={actions.toggleTimelapse}
            className={`p-1.5 rounded-lg border text-xs transition-colors cursor-pointer ${
              state.isPlayingTimelapse
                ? 'bg-amber-500/20 border-amber-500/40 text-amber-300'
                : 'bg-panel-hover border-border text-muted hover:text-text hover:border-blue-bright'
            }`}
            title={state.isPlayingTimelapse ? 'Pause time-lapse' : 'Play 24-hour day/night cycle time-lapse'}
          >
            {state.isPlayingTimelapse ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
          </button>

          {/* 24-Hour Day/Night Slider */}
          <div className="flex-1 relative flex items-center">
            <input
              type="range"
              min="0"
              max="24"
              step="0.1"
              value={sliderValue}
              onChange={handleSliderChange}
              className="w-full h-1.5 bg-gradient-to-r from-indigo-950 via-amber-700/60 via-amber-300/80 via-orange-600/70 to-indigo-950 rounded-lg appearance-none cursor-pointer accent-emerald outline-none"
              title="Drag to simulate day/night rotation around Earth"
            />
          </div>

          {/* Quick Time Presets */}
          <div className="flex items-center gap-1 shrink-0">
            <button
              onClick={() => handleSetPreset(6)}
              className="px-2 py-1 rounded bg-panel-hover border border-border hover:border-border-light text-[10px] font-mono text-muted hover:text-text transition-colors cursor-pointer"
              title="Set to 06:00 UTC (Dawn over Asia / India noon)"
            >
              06:00
            </button>
            <button
              onClick={() => handleSetPreset(12)}
              className="px-2 py-1 rounded bg-panel-hover border border-border hover:border-border-light text-[10px] font-mono text-muted hover:text-text transition-colors cursor-pointer"
              title="Set to 12:00 UTC (Solar Noon over Greenwich)"
            >
              12:00
            </button>
            <button
              onClick={() => handleSetPreset(18)}
              className="px-2 py-1 rounded bg-panel-hover border border-border hover:border-border-light text-[10px] font-mono text-muted hover:text-text transition-colors cursor-pointer"
              title="Set to 18:00 UTC (Sunset over Europe/Africa, Americas noon)"
            >
              18:00
            </button>
            <button
              onClick={() => handleSetPreset(0)}
              className="px-2 py-1 rounded bg-panel-hover border border-border hover:border-border-light text-[10px] font-mono text-muted hover:text-text transition-colors cursor-pointer"
              title="Set to 00:00 UTC (Midnight over Greenwich, Night over India)"
            >
              00:00
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
