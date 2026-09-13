import { Component } from 'react';
import { RefreshCw, AlertTriangle, Terminal, Compass } from 'lucide-react';

export default class GlobeErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('[GlobeErrorBoundary] Caught 3D error:', error, errorInfo);
    this.setState({ errorInfo });
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="w-full h-full min-h-[450px] flex flex-col items-center justify-center p-6 bg-bg-deep text-center select-none">
          <div className="max-w-md w-full glass p-6 rounded-xl border border-rose-500/30 shadow-2xl relative overflow-hidden">
            {/* Ambient background glow */}
            <div className="absolute -top-12 -left-12 w-36 h-36 bg-rose-500/10 rounded-full blur-2xl pointer-events-none" />
            <div className="absolute -bottom-12 -right-12 w-36 h-36 bg-blue-500/10 rounded-full blur-2xl pointer-events-none" />

            <div className="flex items-center justify-center w-12 h-12 rounded-xl bg-rose-500/15 border border-rose-500/30 text-rose-400 mx-auto mb-4">
              <AlertTriangle className="w-6 h-6" />
            </div>

            <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-mono uppercase tracking-wider text-rose-400 bg-rose-500/10 border border-rose-500/20 mb-3">
              <span>3D ENGINE NOTICE</span>
            </div>

            <h3 className="text-base font-semibold text-text mb-2">
              3D Viewport Offline
            </h3>

            <p className="text-xs text-muted leading-relaxed mb-5">
              The 3D WebGL engine encountered a texture or context error. Satellite query, coordinates, and geospatial workflows remain fully active.
            </p>

            <div className="flex items-center justify-center gap-2 mb-4">
              <button
                type="button"
                onClick={this.handleReset}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-medium bg-blue-bright text-bg-deep hover:bg-blue-300 transition-colors shadow-lg shadow-blue-bright/20 cursor-pointer"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                Reload 3D Viewport
              </button>

              <button
                type="button"
                onClick={() => window.location.reload()}
                className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium text-text bg-panel-hover border border-border-light hover:border-text/30 transition-colors cursor-pointer"
              >
                Refresh App
              </button>
            </div>

            {this.state.error && (
              <details className="text-left mt-3">
                <summary className="text-[10px] font-mono text-faint hover:text-muted cursor-pointer flex items-center gap-1">
                  <Terminal className="w-3 h-3 inline" />
                  View Diagnostics
                </summary>
                <div className="mt-2 p-2.5 rounded bg-bg-surface/80 border border-border text-[10px] font-mono text-rose-300/80 overflow-x-auto max-h-32">
                  {this.state.error.message || String(this.state.error)}
                </div>
              </details>
            )}
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
