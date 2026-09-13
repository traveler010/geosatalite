import { useState, useCallback } from 'react';
import { Download, FileText, Loader2, ExternalLink } from 'lucide-react';

const BACKEND_BASE = 'http://localhost:8000';

export default function ReportExport({ queryId }) {
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState(null);

  const handleDownload = useCallback(async () => {
    if (!queryId || downloading) return;
    setDownloading(true);
    setError(null);

    try {
      const response = await fetch(`${BACKEND_BASE}/api/report/${queryId}`);

      if (!response.ok) {
        // If backend unavailable, generate a client-side report
        throw new Error('Backend unavailable');
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `satquery_report_${queryId}.html`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch {
      // Client-side fallback: open report in new tab
      try {
        window.open(`${BACKEND_BASE}/api/report/${queryId}`, '_blank');
      } catch {
        setError('Could not download report. Ensure the backend is running.');
      }
    } finally {
      setDownloading(false);
    }
  }, [queryId, downloading]);

  return (
    <div className="flex items-center gap-2">
      <button
        onClick={handleDownload}
        disabled={downloading}
        className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-border bg-panel-card text-[11px] text-muted hover:text-text hover:border-blue-bright/40 hover:bg-panel-hover transition-all disabled:opacity-50"
      >
        {downloading ? (
          <Loader2 className="w-3.5 h-3.5 animate-spin-slow" />
        ) : (
          <Download className="w-3.5 h-3.5" />
        )}
        Download Report
      </button>

      <a
        href={`${BACKEND_BASE}/api/report/${queryId}`}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center gap-1 px-3 py-2 rounded-lg border border-border bg-panel-card text-[11px] text-muted hover:text-text hover:border-blue-bright/40 hover:bg-panel-hover transition-all"
      >
        <ExternalLink className="w-3.5 h-3.5" />
        Open
      </a>

      {error && (
        <span className="text-[10px] text-red-400">{error}</span>
      )}
    </div>
  );
}
