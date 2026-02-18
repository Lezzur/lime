import { useEffect, useRef, useState } from "react";
import { Edit2, Check, X, Clock } from "lucide-react";
import type { TranscriptSegment } from "../lib/types";
import { api } from "../lib/api";

const SPEAKER_COLORS = [
  "text-sky-400",
  "text-emerald-400",
  "text-violet-400",
  "text-amber-400",
  "text-rose-400",
  "text-cyan-400",
];

interface Props {
  meetingId: string;
  segments: TranscriptSegment[];
  onSegmentUpdated?: (segment: TranscriptSegment) => void;
}

function formatTime(seconds: number) {
  const m = Math.floor(seconds / 60).toString().padStart(2, "0");
  const s = Math.floor(seconds % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
}

interface SegmentRowProps {
  segment: TranscriptSegment;
  colorClass: string;
  meetingId: string;
  onUpdated?: (s: TranscriptSegment) => void;
}

function SegmentRow({ segment, colorClass, meetingId, onUpdated }: SegmentRowProps) {
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState(segment.text);
  const [saving, setSaving] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  function startEdit() {
    setEditing(true);
    setTimeout(() => textareaRef.current?.focus(), 0);
  }

  function cancel() {
    setText(segment.text);
    setEditing(false);
  }

  async function save() {
    if (text.trim() === segment.text) {
      setEditing(false);
      return;
    }
    setSaving(true);
    try {
      const updated = await api.patchTranscriptSegment(meetingId, segment.id, text.trim());
      onUpdated?.(updated);
      setEditing(false);
    } catch (err) {
      console.error("Segment save failed:", err);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="group flex gap-3 py-3 px-4 hover:bg-white/[0.02] rounded-lg transition-colors">
      {/* Time */}
      <div className="flex items-start gap-1.5 pt-0.5 shrink-0 w-16">
        <Clock size={10} className="text-[var(--lime-text-dim)] mt-0.5" />
        <span className="text-[10px] text-[var(--lime-text-dim)] font-mono">
          {formatTime(segment.start_time)}
        </span>
      </div>

      {/* Speaker */}
      <div className="flex items-start pt-0.5 shrink-0 w-24">
        <span className={`text-xs font-medium truncate ${colorClass}`}>
          {segment.speaker_name ?? segment.speaker_label ?? "Speaker"}
        </span>
      </div>

      {/* Text / Editor */}
      <div className="flex-1 min-w-0">
        {editing ? (
          <div className="space-y-1.5">
            <textarea
              ref={textareaRef}
              value={text}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Escape") cancel();
                if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) save();
              }}
              rows={Math.max(2, text.split("\n").length)}
              className="w-full bg-[var(--lime-surface-2)] border border-[var(--lime-border)] rounded px-2 py-1.5 text-sm text-[var(--lime-text)] resize-none outline-none focus:border-[var(--accent)] selectable transition-colors"
            />
            <div className="flex items-center gap-2">
              <button
                onClick={save}
                disabled={saving}
                className="flex items-center gap-1 text-[10px] text-emerald-400 hover:text-emerald-300 transition-colors"
              >
                <Check size={10} /> {saving ? "Saving…" : "Save (⌘↵)"}
              </button>
              <button
                onClick={cancel}
                className="flex items-center gap-1 text-[10px] text-[var(--lime-text-dim)] hover:text-[var(--lime-text-muted)] transition-colors"
              >
                <X size={10} /> Cancel (Esc)
              </button>
            </div>
          </div>
        ) : (
          <div className="flex items-start gap-2">
            <p className="text-sm text-[var(--lime-text)] leading-relaxed selectable flex-1">
              {text}
            </p>
            <button
              onClick={startEdit}
              className="opacity-0 group-hover:opacity-100 p-1 rounded text-[var(--lime-text-dim)] hover:text-[var(--lime-text-muted)] hover:bg-white/5 transition-all shrink-0"
              title="Correct transcript"
            >
              <Edit2 size={11} />
            </button>
          </div>
        )}
      </div>

      {/* Confidence */}
      {segment.confidence !== undefined && (
        <div className="shrink-0 pt-0.5">
          <span
            className={`text-[10px] font-mono ${
              segment.confidence >= 0.8
                ? "text-[var(--lime-text-dim)]"
                : "text-amber-500"
            }`}
          >
            {Math.round(segment.confidence * 100)}%
          </span>
        </div>
      )}
    </div>
  );
}

export default function TranscriptView({ meetingId, segments: initial }: Props) {
  const [segments, setSegments] = useState(initial);
  const [loading, setLoading] = useState(initial.length === 0);

  const speakerColorMap = useRef<Map<string, string>>(new Map());

  function getColor(segment: TranscriptSegment) {
    const key = segment.speaker_label ?? segment.speaker_id ?? "?";
    if (!speakerColorMap.current.has(key)) {
      const idx = speakerColorMap.current.size % SPEAKER_COLORS.length;
      speakerColorMap.current.set(key, SPEAKER_COLORS[idx]);
    }
    return speakerColorMap.current.get(key)!;
  }

  useEffect(() => {
    if (initial.length === 0) {
      api
        .getMeetingTranscript(meetingId)
        .then(setSegments)
        .catch(console.error)
        .finally(() => setLoading(false));
    }
  }, [meetingId, initial.length]);

  function handleUpdated(updated: TranscriptSegment) {
    setSegments((prev) => prev.map((s) => (s.id === updated.id ? updated : s)));
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center p-12 text-[var(--lime-text-muted)] text-sm">
        Loading transcript…
      </div>
    );
  }

  if (segments.length === 0) {
    return (
      <div className="flex items-center justify-center p-12 text-[var(--lime-text-muted)] text-sm">
        No transcript available yet.
      </div>
    );
  }

  return (
    <div className="p-4 space-y-0.5">
      {/* Header */}
      <div className="flex gap-3 px-4 pb-2 mb-2 border-b border-[var(--lime-border)]">
        <span className="text-[10px] uppercase tracking-widest text-[var(--lime-text-dim)] w-16">Time</span>
        <span className="text-[10px] uppercase tracking-widest text-[var(--lime-text-dim)] w-24">Speaker</span>
        <span className="text-[10px] uppercase tracking-widest text-[var(--lime-text-dim)] flex-1">Transcript</span>
        <span className="text-[10px] uppercase tracking-widest text-[var(--lime-text-dim)]">Conf</span>
      </div>

      {segments.map((segment) => (
        <SegmentRow
          key={segment.id}
          segment={segment}
          colorClass={getColor(segment)}
          meetingId={meetingId}
          onUpdated={handleUpdated}
        />
      ))}
    </div>
  );
}
