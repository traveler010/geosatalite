import { MapPin } from 'lucide-react';
import { useAppStore, LOCATIONS } from '../store/useAppStore';

const QUICK_LOCATIONS = [
  'Sriharikota Spaceport',
  'Mumbai Port / JNPT',
  'Pangong Tso Basin',
  'Delhi IGI Airport Runway',
];

export default function QuickLocations() {
  const { actions } = useAppStore();

  const handleClick = (name) => {
    const location = LOCATIONS[name];
    if (location) {
      actions.flyTo(location, name);
      actions.addMessage('assistant',
        `Flying to ${name}. Analysis zone updated.`,
        'NAVIGATION / QUICK LOCATION'
      );
    }
  };

  return (
    <div className="absolute bottom-4 left-4 right-4 z-10 flex flex-wrap gap-[7px]">
      {QUICK_LOCATIONS.map((name) => (
        <button
          key={name}
          onClick={() => handleClick(name)}
          className="glass-pill inline-flex items-center gap-1.5 px-2.5 py-[7px] rounded-full text-[10px] text-[#d4dfec] hover:border-emerald hover:text-emerald-light hover:bg-emerald/15 hover:-translate-y-0.5 transition-all duration-200"
        >
          <MapPin className="w-3 h-3" />
          {name}
        </button>
      ))}
    </div>
  );
}
