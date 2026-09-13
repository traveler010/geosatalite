import { useState, useCallback } from 'react';
import { Search, Navigation } from 'lucide-react';
import { useAppStore, LOCATIONS } from '../store/useAppStore';
import { geocodeLocation, parseCoordinates } from '../services/api';

export default function SearchHUD() {
  const [query, setQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const { actions } = useAppStore();

  const handleFlyTo = useCallback(async () => {
    const value = query.trim();
    if (!value || isSearching) return;

    // 1. Try parsing as coordinates
    const coords = parseCoordinates(value);
    if (coords) {
      actions.flyTo(
        { latitude: coords.lat, longitude: coords.lng, altitude: 3000 },
        value
      );
      actions.addMessage('assistant',
        `Navigating to coordinates ${coords.lat.toFixed(4)}°, ${coords.lng.toFixed(4)}°`,
        'NAVIGATION / COORDINATE INPUT'
      );
      return;
    }

    // 2. Check predefined locations
    const key = Object.keys(LOCATIONS).find(
      name => name.toLowerCase().includes(value.toLowerCase()) ||
        value.toLowerCase().includes(name.toLowerCase())
    );
    if (key) {
      actions.flyTo(LOCATIONS[key], key);
      actions.addMessage('assistant',
        `Flying to ${key}. Analysis zone updated.`,
        'NAVIGATION / PREDEFINED LOCATION'
      );
      return;
    }

    // 3. Use Nominatim API geocoding
    setIsSearching(true);
    actions.addMessage('assistant',
      `Searching for "${value}" via OpenStreetMap Nominatim...`,
      'GEOCODING / API QUERY'
    );

    const result = await geocodeLocation(value);
    setIsSearching(false);

    if (result) {
      actions.flyTo(
        { latitude: result.lat, longitude: result.lng, altitude: 3000 },
        result.displayName.split(',')[0]
      );
      actions.addMessage('assistant',
        `Location resolved: ${result.displayName}`,
        `NOMINATIM / ${result.lat.toFixed(4)}°, ${result.lng.toFixed(4)}°`
      );
    } else {
      actions.addMessage('assistant',
        `Could not resolve "${value}". Try coordinates like 28.6139, 77.2090 or use a quick location pill.`,
        'NAVIGATION / LOCATION NOT RESOLVED'
      );
    }
  }, [query, isSearching, actions]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleFlyTo();
    }
  };

  return (
    <div className="absolute top-4 left-4 right-4 z-10 flex gap-2">
      <div className="relative flex-1">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-faint pointer-events-none" />
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Search location or coordinates · e.g. Sriharikota or 28.6139, 77.2090"
          className="w-full h-[39px] pl-9 pr-3 glass-search rounded-[9px] outline-none text-text text-[11px] focus:border-blue-bright focus:shadow-[0_0_0_3px_rgba(56,189,248,0.12)] transition-all"
        />
      </div>
      <button
        onClick={handleFlyTo}
        disabled={isSearching}
        className="h-[39px] px-3 flex items-center gap-1.5 rounded-[9px] border border-blue bg-blue/80 text-white text-[11px] font-medium hover:bg-blue-hover transition-all disabled:opacity-60 disabled:cursor-wait"
      >
        <Navigation className="w-3.5 h-3.5" />
        {isSearching ? 'Searching...' : 'Fly To'}
      </button>
    </div>
  );
}
