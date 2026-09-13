import { Satellite } from 'lucide-react';

export default function TopBar() {
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
