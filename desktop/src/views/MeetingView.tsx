import { useState } from "react";
import { useMeetingStore } from "../stores/meetingStore";
import MeetingsListView from "./MeetingsListView";
import MeetingDetailView from "./MeetingDetailView";
import SearchView from "./SearchView";
import SettingsView from "./SettingsView";
import RecordingBar from "../components/RecordingBar";

function MemoryView() {
  return (
    <div className="flex items-center justify-center h-full text-[var(--lime-text-muted)] text-sm">
      Memory view — coming in next sprint
    </div>
  );
}

function MemosView() {
  return (
    <div className="flex items-center justify-center h-full text-[var(--lime-text-muted)] text-sm">
      Voice Memos — coming in Phase 4
    </div>
  );
}

export default function MeetingView() {
  const { activeView } = useMeetingStore();
  const [detailId, setDetailId] = useState<string | null>(null);

  if (activeView === "settings") return <SettingsView />;
  if (activeView === "search") return <SearchView />;
  if (activeView === "memory") return <MemoryView />;
  if (activeView === "memos") return <MemosView />;

  // Meetings view with list + detail
  return (
    <div className="flex h-full">
      {/* Left panel: recording bar + list */}
      <div className="w-72 shrink-0 border-r border-[var(--lime-border)] flex flex-col">
        <RecordingBar />
        <div className="flex-1 overflow-hidden">
          <MeetingsListView onSelectMeeting={setDetailId} />
        </div>
      </div>

      {/* Right panel: detail or empty state */}
      <div className="flex-1 overflow-hidden">
        {detailId ? (
          <MeetingDetailView meetingId={detailId} onBack={() => setDetailId(null)} />
        ) : (
          <div className="flex flex-col items-center justify-center h-full gap-2 text-center">
            <p className="text-[var(--lime-text-muted)] text-sm">Select a meeting to view</p>
            <p className="text-xs text-[var(--lime-text-dim)]">
              or start a new recording
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
