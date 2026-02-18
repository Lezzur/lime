import { useEffect } from "react";
import Sidebar from "./components/Sidebar";
import MeetingView from "./views/MeetingView";
import { useMeetingStore } from "./stores/meetingStore";

function App() {
  const { isRecording, personalityMode } = useMeetingStore();

  // Apply personality theme to root
  useEffect(() => {
    document.documentElement.dataset.personality = personalityMode;
  }, [personalityMode]);

  return (
    <div className="flex h-screen w-screen bg-[var(--lime-bg)] overflow-hidden">
      <Sidebar />
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="flex items-center justify-between px-5 py-2.5 border-b border-[var(--lime-border)] shrink-0">
          <h1 className="text-sm font-semibold tracking-tight" style={{ color: "var(--accent)" }}>
            LIME
          </h1>
          <div className="flex items-center gap-3">
            {isRecording && (
              <span className="flex items-center gap-2 text-xs text-red-400">
                <span className="h-1.5 w-1.5 rounded-full bg-red-500 animate-pulse" />
                Live
              </span>
            )}
          </div>
        </header>

        {/* Main content */}
        <div className="flex-1 overflow-hidden">
          <MeetingView />
        </div>
      </main>
    </div>
  );
}

export default App;
