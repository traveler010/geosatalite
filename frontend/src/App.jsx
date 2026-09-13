import { AppStoreProvider } from './store/useAppStore';
import TopBar from './components/TopBar';
import GlobePanel from './components/GlobePanel';
import SidePanel from './components/SidePanel';

export default function App() {
  return (
    <AppStoreProvider>
      <main className="min-h-screen p-[18px] max-sm:p-2.5">
        <TopBar />
        <section className="grid grid-cols-[minmax(0,1.85fr)_minmax(360px,1fr)] gap-3.5 max-w-[1800px] min-h-[calc(100vh-120px)] mx-auto max-md:grid-cols-1">
          <GlobePanel />
          <SidePanel />
        </section>
      </main>
    </AppStoreProvider>
  );
}
