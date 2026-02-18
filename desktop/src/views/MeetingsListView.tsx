import { useEffect, useState, useCallback } from "react";
import { Search, Mic } from "lucide-react";
import { format, parseISO, isToday, isYesterday, isThisWeek } from "date-fns";
import type { Meeting } from "../lib/types";
import { api } from "../lib/api";
import { useMeetingStore } from "../stores/meetingStore";

const STATUS_COLORS: Record<string, string> = {
  recording: "text-red-400",
  processing: "text-amber-400",
  completed: "text-emerald-400",
  failed: "text-red-500",
};

function formatDuration(seconds?: number) {
  if (!seconds) return "--";
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

function groupDate(dateStr: string): string {
  const d = parseISO(dateStr);
  if (isToday(d)) return "Today";
  if (isYesterday(d)) return "Yesterday";
  if (isThisWeek(d)) return "This Week";
  return format(d, "MMMM yyyy");
}

function MeetingRow({ meeting, isSelected, onClick }: {
  meeting: Meeting;
  isSelected: boolean;
  onClick: () => void;
}) {
  const date = parseISO(meeting.started_at);

  return (
    <button
      onClick={onClick}
      className={`w-full flex items-start gap-3 px-3 py-2.5 rounded-lg text-left transition-colors ${
        isSelected ? "bg-white/10" : "hover:bg-white/5"
      }`}
    >
      <div className="h-8 w-8 rounded-md bg-[var(--lime-surface-2)] border border-[var(--lime-border)] flex items-center justify-center shrink-0 mt-0.5">
        <Mic size={13} className="text-[var(--lime-text-dim)]" />
      </div>

      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-[var(--lime-text)] truncate">
          {meeting.title ?? `Meeting – ${format(date, "h:mm a")}`}
        </p>
        <div className="flex items-center gap-2 mt-0.5">
          <span className={`text-[10px] ${STATUS_COLORS[meeting.status] ?? "text-[var(--lime-text-dim)]"}`}>
            {meeting.status}
          </span>
          <span className="text-[10px] text-[var(--lime-text-dim)]">
            {formatDuration(meeting.duration_seconds)}
          </span>
          <span className="text-[10px] text-[var(--lime-text-dim)]">
            {format(date, "h:mm a")}
          </span>
        </div>
      </div>
    </button>
  );
}

interface Props {
  onSelectMeeting: (id: string) => void;
}

export default function MeetingsListView({ onSelectMeeting }: Props) {
  const { meetings, setMeetings, selectedMeetingId, selectMeeting, isRecording } = useMeetingStore();
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>("all");

  const load = useCallback(async () => {
    try {
      const data = await api.getMeetings();
      setMeetings(data);
    } catch (err) {
      console.error("Failed to load meetings:", err);
    } finally {
      setLoading(false);
    }
  }, [setMeetings]);

  useEffect(() => {
    load();
  }, [load]);

  // Refresh when recording stops
  useEffect(() => {
    if (!isRecording) load();
  }, [isRecording, load]);

  const filtered = meetings.filter((m) => {
    const matchesSearch =
      !search ||
      (m.title ?? "").toLowerCase().includes(search.toLowerCase()) ||
      m.id.includes(search);
    const matchesStatus = statusFilter === "all" || m.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  // Group by date
  const groups: Record<string, Meeting[]> = {};
  for (const m of filtered) {
    const g = groupDate(m.started_at);
    if (!groups[g]) groups[g] = [];
    groups[g].push(m);
  }

  function handleSelect(id: string) {
    selectMeeting(id);
    onSelectMeeting(id);
  }

  return (
    <div className="flex flex-col h-full">
      {/* Search + filter bar */}
      <div className="px-3 py-3 border-b border-[var(--lime-border)] space-y-2">
        <div className="relative">
          <Search
            size={13}
            className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[var(--lime-text-dim)]"
          />
          <input
            type="text"
            placeholder="Search meetings…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-[var(--lime-surface-2)] border border-[var(--lime-border)] rounded-md pl-8 pr-3 py-1.5 text-xs text-[var(--lime-text)] placeholder:text-[var(--lime-text-dim)] outline-none focus:border-[var(--accent)] transition-colors selectable"
          />
        </div>

        <div className="flex gap-1">
          {["all", "completed", "processing", "recording", "failed"].map((s) => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={`px-2 py-0.5 rounded text-[10px] capitalize transition-colors ${
                statusFilter === s
                  ? "text-[var(--accent-text)] font-medium"
                  : "text-[var(--lime-text-dim)] hover:text-[var(--lime-text-muted)]"
              }`}
              style={statusFilter === s ? { backgroundColor: "var(--accent)" } : {}}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto px-2 py-2">
        {loading ? (
          <p className="text-xs text-[var(--lime-text-dim)] px-3 py-4">Loading…</p>
        ) : filtered.length === 0 ? (
          <p className="text-xs text-[var(--lime-text-dim)] px-3 py-4">
            {search ? "No meetings match your search." : "No meetings yet. Start a recording."}
          </p>
        ) : (
          Object.entries(groups).map(([group, items]) => (
            <div key={group} className="mb-3">
              <p className="text-[10px] uppercase tracking-widest text-[var(--lime-text-dim)] px-3 py-1">
                {group}
              </p>
              {items.map((m) => (
                <MeetingRow
                  key={m.id}
                  meeting={m}
                  isSelected={selectedMeetingId === m.id}
                  onClick={() => handleSelect(m.id)}
                />
              ))}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
