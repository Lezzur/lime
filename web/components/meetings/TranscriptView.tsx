"use client";

import { useCallback, useRef, useState } from "react";
import type { TranscriptSegment, TopicSegment } from "@/lib/types";
import { ConfidenceBadge } from "@/components/ui/ConfidenceBadge";
import { correctTranscript } from "@/lib/api";
import { cn, formatDuration } from "@/lib/utils";
import { Edit2, Check, X, MapPin } from "lucide-react";

interface TranscriptViewProps {
  meetingId: string;
  segments: TranscriptSegment[];
  topics?: TopicSegment[];
  onSeek?: (time: number) => void;
  highlightTime?: number;
}

function getTopicAtTime(topics: TopicSegment[], time: number): TopicSegment | null {
  return topics.find((t) => time >= t.start_time && time <= t.end_time) ?? null;
}

export function TranscriptView({
  meetingId,
  segments,
  topics = [],
  onSeek,
  highlightTime,
}: TranscriptViewProps) {
  const [editing, setEditing] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState<Record<string, boolean>>({});
  const [saved, setSaved] = useState<Record<string, boolean>>({});
  const containerRef = useRef<HTMLDivElement>(null);

  const startEdit = useCallback((seg: TranscriptSegment) => {
    setEditing((v) => ({ ...v, [seg.id]: seg.text }));
  }, []);

  const cancelEdit = useCallback((id: string) => {
    setEditing((v) => {
      const next = { ...v };
      delete next[id];
      return next;
    });
  }, []);

  const saveEdit = useCallback(
    async (seg: TranscriptSegment) => {
      const corrected = editing[seg.id];
      if (!corrected || corrected === seg.text) {
        cancelEdit(seg.id);
        return;
      }
      setSaving((v) => ({ ...v, [seg.id]: true }));
      try {
        await correctTranscript(meetingId, seg.id, corrected);
        setSaved((v) => ({ ...v, [seg.id]: true }));
        setTimeout(() => setSaved((v) => ({ ...v, [seg.id]: false })), 2000);
      } finally {
        setSaving((v) => ({ ...v, [seg.id]: false }));
        cancelEdit(seg.id);
      }
    },
    [editing, meetingId, cancelEdit]
  );

  let lastTopicId: string | null = null;

  return (
    <div ref={containerRef} className="space-y-1">
      {segments.map((seg) => {
        const topic = getTopicAtTime(topics, seg.start_time);
        const showTopicBoundary = topic && topic.id !== lastTopicId;
        if (showTopicBoundary) lastTopicId = topic.id;

        const isHighlighted =
          highlightTime !== undefined &&
          highlightTime >= seg.start_time &&
          highlightTime <= seg.end_time;

        return (
          <div key={seg.id}>
            {/* Topic boundary marker */}
            {showTopicBoundary && (
              <div className="flex items-center gap-3 py-3 my-2">
                <MapPin className="w-4 h-4 text-zinc-600 flex-shrink-0" />
                <div className="flex-1 h-px bg-zinc-800" />
                <span className="text-xs text-zinc-500 font-medium px-2 bg-zinc-950">
                  {topic!.title}
                </span>
                <div className="flex-1 h-px bg-zinc-800" />
              </div>
            )}

            {/* Segment */}
            <div
              className={cn(
                "group flex items-start gap-3 px-3 py-2 rounded-lg transition-colors",
                isHighlighted ? "bg-lime-900/20" : "hover:bg-zinc-900/50"
              )}
            >
              {/* Timestamp */}
              <button
                onClick={() => onSeek?.(seg.start_time)}
                className="text-zinc-600 text-xs font-mono mt-0.5 hover:text-lime-400 transition-colors flex-shrink-0 tabular-nums"
                title="Play from here"
              >
                {formatDuration(seg.start_time)}
              </button>

              {/* Speaker */}
              {seg.speaker && (
                <span className="text-zinc-500 text-xs font-medium mt-0.5 flex-shrink-0 w-20 truncate">
                  {seg.speaker}
                </span>
              )}

              {/* Text */}
              <div className="flex-1 min-w-0">
                {editing[seg.id] !== undefined ? (
                  <div className="space-y-2">
                    <textarea
                      value={editing[seg.id]}
                      onChange={(e) =>
                        setEditing((v) => ({ ...v, [seg.id]: e.target.value }))
                      }
                      className="w-full bg-zinc-800 text-zinc-200 text-sm rounded-lg p-2 border border-zinc-700 outline-none resize-none"
                      rows={3}
                      autoFocus
                    />
                    <div className="flex gap-2">
                      <button
                        onClick={() => saveEdit(seg)}
                        disabled={saving[seg.id]}
                        className="flex items-center gap-1 text-xs text-lime-400 hover:text-lime-300"
                      >
                        <Check className="w-3.5 h-3.5" />
                        {saving[seg.id] ? "Saving…" : "Save"}
                      </button>
                      <button
                        onClick={() => cancelEdit(seg.id)}
                        className="flex items-center gap-1 text-xs text-zinc-500 hover:text-zinc-400"
                      >
                        <X className="w-3.5 h-3.5" />
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  <p
                    className={cn(
                      "text-sm leading-relaxed",
                      seg.is_low_confidence ? "text-zinc-500" : "text-zinc-300",
                      saved[seg.id] && "text-green-400"
                    )}
                  >
                    {seg.text}
                    {seg.is_low_confidence && (
                      <ConfidenceBadge
                        confidence={seg.confidence ?? 0}
                        className="ml-2"
                      />
                    )}
                  </p>
                )}
              </div>

              {/* Edit button */}
              {editing[seg.id] === undefined && (
                <button
                  onClick={() => startEdit(seg)}
                  className="opacity-0 group-hover:opacity-100 text-zinc-600 hover:text-zinc-400 transition-all flex-shrink-0 mt-0.5"
                >
                  <Edit2 className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
