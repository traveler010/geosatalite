import { NavLink, useLocation } from 'react-router-dom';
import { Globe, Upload, MessageSquareText, FileText, Satellite } from 'lucide-react';

const NAV_ITEMS = [
  { to: '/', label: 'Home', icon: Globe },
  { to: '/upload', label: 'Upload', icon: Upload },
  { to: '/query', label: 'Query', icon: MessageSquareText },
  { to: '/reports', label: 'Reports', icon: FileText },
];

export default function Navigation() {
  const location = useLocation();

  return (
    <header className="glass flex items-center justify-between gap-4 max-w-[1800px] min-h-[70px] mx-auto mb-3.5 px-[18px] py-[13px] rounded-[14px] max-sm:flex-col max-sm:items-start max-sm:p-[13px]">
      {/* Brand */}
      <div className="flex items-center gap-[11px]">
        <div className="grid place-items-center w-[42px] h-[42px] border border-blue-bright/45 rounded-[11px] bg-blue/15 text-[21px]">
          <Satellite className="w-5 h-5 text-blue-bright" />
        </div>
        <div>
          <h1 className="m-0 text-lg font-bold tracking-tight text-text">
            SatQuery AI
          </h1>
          <p className="mt-0.5 text-[11px] text-muted">
            ISRO Multimodal Remote Sensing Assistant · PS 167
          </p>
        </div>
      </div>

      {/* Nav Links */}
      <nav className="flex items-center gap-1 max-sm:w-full max-sm:overflow-x-auto">
        {NAV_ITEMS.map(({ to, label, icon: Icon }) => {
          const isActive = location.pathname === to;
          return (
            <NavLink
              key={to}
              to={to}
              className={`inline-flex items-center gap-1.5 px-3.5 py-[9px] rounded-lg text-[11px] font-medium transition-all duration-200 border ${
                isActive
                  ? 'border-blue-bright/50 bg-blue/20 text-blue-bright shadow-[0_0_12px_rgba(56,189,248,0.1)]'
                  : 'border-transparent text-muted hover:text-text hover:bg-panel-hover'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              {label}
            </NavLink>
          );
        })}
      </nav>

      {/* Status Badge */}
      <div className="inline-flex items-center gap-2 px-3 py-2 border border-emerald/30 rounded-full bg-emerald/[0.09] text-emerald-light font-mono text-[10px] whitespace-nowrap max-sm:self-stretch max-sm:justify-center">
        <span className="w-[7px] h-[7px] rounded-full bg-emerald shadow-[0_0_12px] shadow-emerald animate-pulse-glow" />
        System Online
        <span className="text-faint">|</span>
        CRS: EPSG:4326
      </div>
    </header>
  );
}
