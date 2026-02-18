import { useEffect, useState } from "react";
import { format, parseISO } from "date-fns";
import { ArrowLeft, Loader2 } from "lucide-react";
import type { TranscriptSegment } from "../lib/types";
import { api } from "../lib/api";
import { useMeetingStore } from "../stores/meetingStore";
import ExecutiveSummary from "../components/ExecutiveSummary";
import TranscriptView from "../components/TranscriptView";
import TopicTimeline from "../components/TopicTimeline";

type SubView = "summary" | "transcript" | "topics";

const TABS: { id: SubView; label: string }[] = [
  { id: "summary", label: "Summary" },
  { id: "topics", label: "Topics" },
  { id: "transcript", label: "Transcript" },
];

interface Props {
  meetingId: string;
  onBack: () => void;
}

export default function MeetingDetailView({ meetingId, onBack }: Props) {
  const { selectedMeetingNotes, setMeetingNotes, meetings } = useMeetingStore();
  const [subView, setSubView] = useState<SubView>("summary");
  const [segments, setSegments] = useState<TranscriptSegment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const meeting = meetings.find((m) => m.id === meetingId);

  useEffect(() => {
    setLoading(true);
    setError(null);

    api
      .getMeetingNotes(meetingId)
      .then((notes) => setMeetingNotes(notes))
      .catch((err) => {
        console.error("Notes load failed:", err);
        setError("Failed to load meeting data.");
      })
      .finally(() => setLoading(false));
  }, [meetingId, setMeetingNotes]);

  // Prefetch transcript in background
  useEffect(() => {
    api
      .getMeetingTranscript(meetingId)
      .then(setSegments)
      .catch(console.error);
  }, [meetingId]);

  const dateStr = meeting?.started_at
    ? format(parseISO(meeting.started_at), "EEEE, MMMM d · h:mm a")
    : null;

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-[var(--lime-border)] shrink-0">
        <button
          onClick={onBack}
          className="p-1 rounded text-[var(--lime-text-muted)] hover:text-[var(--lime-text)] hover:bg-white/5 transition-colors"
        >
          <ArrowLeft size={15} />
        </button>
        <div className="flex-1 min-w-0">
          <h2 className="text-sm font-semibold text-[var(--lime-text)] truncate">
            {meeting?.title ?? "Meeting"}
          </h2>
          {dateStr && (
            <p className="text-[10px] text-[var(--lime-text-muted)]">{dateStr}</p>
          )}
        </div>

        {/* Status badge */}
        {meeting?.status === "processing" && (
          <span className="flex items-center gap-1.5 text-xs text-amber-400">
            <Loader2 size={11} className="animate-spin" />
            Analyzing…
          </span>
        )}
      </div>

      {/* Sub-view tabs */}
      <div className="flex gap-1 px-4 py-2 border-b border-[var(--lime-border)] shrink-0">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setSubView(tab.id)}
            className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
              subView === tab.id
                ? "text-[var(--accent-text)]"
                : "text-[var(--lime-text-muted)] hover:text-[var(--lime-text)] hover:bg-white/5"
            }`}
            style={subView === tab.id ? { backgroundColor: "var(--accent)" } : {}}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="flex items-center justify-center gap-2 p-12 text-[var(--lime-text-muted)] text-sm">
            <Loader2 size={16} className="animate-spin" />
            Loading…
          </div>
        ) : error ? (
          <div className="p-6 text-sm text-red-400">{error}</div>
        ) : selectedMeetingNotes ? (
          <>
            {subView === "summary" && (
              <ExecutiveSummary meetingId={meetingId} notes={selectedMeetingNotes} />
            )}
            {subView === "topics" && (
              <TopicTimeline
                topics={selectedMeetingNotes.topics ?? []}
                totalDuration={meeting?.duration_seconds}
              />
            )}
            {subView === "transcript" && (
              <TranscriptView meetingId={meetingId} segments={segments} />
            )}
          </>
        ) : (
          <div className="p-6 text-sm text-[var(--lime-text-muted)]">No data available.</div>
        )}
      </div>
    </div>
  );
}
