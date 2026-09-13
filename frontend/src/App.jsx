import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Suspense } from 'react';
import { AppStoreProvider } from './store/useAppStore';
import Navigation from './components/Navigation';
import GlobePanel from './components/GlobePanel';
import SidePanel from './components/SidePanel';
import UploadWorkspace from './components/UploadWorkspace';
import QueryWorkspace from './components/QueryWorkspace';
import ReportsPage from './components/ReportsPage';
import GlobeErrorBoundary from './components/GlobeErrorBoundary';

function HomePage() {
  return (
    <section className="grid grid-cols-[minmax(0,1.85fr)_minmax(360px,1fr)] gap-3.5 max-w-[1800px] min-h-[calc(100vh-120px)] mx-auto max-md:grid-cols-1">
      <GlobePanel />
      <SidePanel />
    </section>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppStoreProvider>
        <main className="min-h-screen p-[18px] max-sm:p-2.5">
          <Navigation />
          <GlobeErrorBoundary>
            <Suspense
              fallback={
                <div className="flex items-center justify-center min-h-[60vh]">
                  <div className="text-center">
                    <div className="w-10 h-10 mx-auto mb-3 border-2 border-blue-bright/30 border-t-blue-bright rounded-full animate-spin-slow" />
                    <p className="text-muted text-xs font-mono">Loading workspace...</p>
                  </div>
                </div>
              }
            >
              <Routes>
                <Route path="/" element={<HomePage />} />
                <Route path="/upload" element={<UploadWorkspace />} />
                <Route path="/query" element={<QueryWorkspace />} />
                <Route path="/reports" element={<ReportsPage />} />
              </Routes>
            </Suspense>
          </GlobeErrorBoundary>
        </main>
      </AppStoreProvider>
    </BrowserRouter>
  );
}
