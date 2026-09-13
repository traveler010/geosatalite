import { Suspense } from 'react';
import { useAppStore } from '../store/useAppStore';
import { formatCoordinate } from '../services/api';
import EarthGlobe from './EarthGlobe';
import GlobeErrorBoundary from './GlobeErrorBoundary';
import SearchHUD from './SearchHUD';
import QuickLocations from './QuickLocations';
import { Upload, Eye } from 'lucide-react';

export default function GlobePanel() {
  const { state, actions } = useAppStore();

  const handleModalityChange = (e) => {
    actions.setModality(e.target.value);
  };

  const handleUpload = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      actions.setUpload(file, reader.result);
      actions.addMessage('assistant',
        'Local image loaded and projected over the active coordinates. The beacon marks the footprint center.',
        'LOCAL ASSET / GEOREFERENCED RECTANGLE READY'
      );
    };
    reader.readAsDataURL(file);
  };

  return (
    <section
      className="glass rounded-[14px] overflow-hidden flex flex-col min-h-[700px] max-md:min-h-[620px]"
      aria-label="Interactive 3D Earth viewport"
    >
      {/* Header */}
      <div className="flex items-center justify-between gap-3 px-[15px] py-3 border-b border-border bg-panel-solid/95 z-[5] max-sm:flex-col max-sm:items-start">
        <div>
          <span className="font-mono text-[10px] tracking-[0.08em] uppercase text-faint">
            3D Digital Earth / Geospatial Command
          </span>
          <strong className="block mt-[3px] text-sm font-bold text-text" id="location-title">
            {state.locationLabel
              ? `${state.locationLabel} / active analysis zone`
              : 'Global satellite intelligence layer'}
          </strong>
        </div>
        <div className="flex items-center gap-[7px] max-sm:w-full">
          <select
            onChange={handleModalityChange}
            value={state.modality}
            className="min-h-[34px] px-2.5 border border-border-light rounded-lg outline-none bg-panel-hover text-text text-[11px] max-sm:flex-1 max-sm:min-w-0"
          >
            <option>Optical RGB</option>
            <option>Synthetic Aperture Radar</option>
          </select>
          <label className="inline-flex items-center justify-center gap-1.5 min-h-[34px] px-[11px] border border-border-light rounded-lg bg-panel-hover text-text text-[11px] hover:border-blue-bright hover:bg-blue/20 hover:text-[#d9f4ff] transition-all duration-200 cursor-pointer max-sm:shrink-0">
            <Upload className="w-3.5 h-3.5" />
            Upload Image / GeoTIFF
            <input
              type="file"
              accept="image/*,.tif,.tiff"
              onChange={handleUpload}
              className="hidden"
            />
          </label>
        </div>
      </div>

      {/* Globe Container */}
      <div className="relative flex-1 min-h-0 overflow-hidden bg-bg-deep">
        {/* Search Overlay */}
        <SearchHUD />

        {/* View Mode Readout */}
        <div className="absolute top-[65px] left-4 z-10 px-[9px] py-[7px] glass-readout rounded-[7px] font-mono text-[9px] text-[#b8c9da]">
          <Eye className="inline-block w-3 h-3 mr-1 -mt-0.5" />
          VIEW MODE <strong className="text-emerald font-medium">3D / TERRAIN</strong> · MOUSE NAVIGATION ENABLED
        </div>

        {/* 3D Earth Viewport */}
        <GlobeErrorBoundary>
          <Suspense
            fallback={
              <div className="w-full h-full flex items-center justify-center bg-bg-deep">
                <div className="text-center">
                  <div className="w-10 h-10 mx-auto mb-3 border-2 border-blue-bright/30 border-t-blue-bright rounded-full animate-spin-slow" />
                  <p className="text-muted text-xs font-mono">Initializing 3D Geospatial Engine...</p>
                </div>
              </div>
            }
          >
            <EarthGlobe />
          </Suspense>
        </GlobeErrorBoundary>

        {/* Quick Locations */}
        <QuickLocations />
      </div>

      {/* Footer */}
      <div className="flex justify-between gap-3 px-[14px] py-[9px] border-t border-border bg-panel-solid font-mono text-[10px] text-muted max-sm:flex-col max-sm:items-start max-sm:gap-[3px]">
        <span>
          ACTIVE FOOTPRINT ·{' '}
          {formatCoordinate(state.activeLocation.latitude, 'N', 'S')},{' '}
          {formatCoordinate(state.activeLocation.longitude, 'E', 'W')}
        </span>
        <span className="text-emerald">
          {state.entityCount} ANALYSIS ENTITIES
        </span>
      </div>
    </section>
  );
}
