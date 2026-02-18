"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getMeetings } from "@/lib/api";
import type { Meeting } from "@/lib/types";
import { formatRelative, formatDuration, cn } from "@/lib/utils";
import { Mic, Monitor, Clock, CheckCircle, AlertCircle, Loader } from "lucide-react";

const statusIcon: Record<Meeting["status"], React.ReactNode> = {
  recording: <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />,
  processing: <Loader className="w-3.5 h-3.5 text-amber-400 animate-spin" />,
  completed: <CheckCircle className="w-3.5 h-3.5 text-green-500" />,
  failed: <AlertCircle className="w-3.5 h-3.5 text-red-500" />,
};

export function MeetingList() {
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getMeetings()
      .then(setMeetings)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader className="w-6 h-6 text-zinc-500 animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-24 text-zinc-500">
        <AlertCircle className="w-8 h-8 mx-auto mb-3 text-zinc-700" />
        <p className="text-sm">{error}</p>
        <p className="text-xs mt-1 text-zinc-600">Is the backend running?</p>
      </div>
    );
  }

  if (meetings.length === 0) {
    return (
      <div className="text-center py-24 text-zinc-500">
        <Mic className="w-10 h-10 mx-auto mb-4 text-zinc-700" />
        <p className="text-sm">No meetings yet</p>
        <p className="text-xs mt-1 text-zinc-600">Start a recording from the desktop app or capture screen</p>
      </div>
    );
  }

  return (
    <div className="divide-y divide-zinc-900">
      {meetings.map((m) => (
        <Link
          key={m.id}
          href={`/meetings/${m.id}`}
          className="flex items-center gap-4 px-6 py-4 hover:bg-zinc-900/50 transition-colors group"
        >
          {/* Source icon */}
          <div className="w-9 h-9 rounded-lg bg-zinc-900 flex items-center justify-center flex-shrink-0 group-hover:bg-zinc-800 transition-colors">
            {m.audio_source === "system" ? (
              <Monitor className="w-4 h-4 text-zinc-500" />
            ) : (
              <Mic className="w-4 h-4 text-zinc-500" />
            )}
          </div>

          {/* Info */}
          <div className="flex-1 min-w-0">
            <p className="text-white text-sm font-medium truncate">
              {m.title ?? "Untitled Meeting"}
            </p>
            <p className="text-zinc-500 text-xs mt-0.5">
              {formatRelative(m.started_at)}
              {m.segment_count > 0 && ` · ${m.segment_count} segments`}
            </p>
          </div>

          {/* Duration */}
          {m.duration_seconds !== null && (
            <div className="flex items-center gap-1.5 text-zinc-600 text-xs flex-shrink-0">
              <Clock className="w-3 h-3" />
              {formatDuration(m.duration_seconds)}
            </div>
          )}

          {/* Status */}
          <div className="flex-shrink-0">{statusIcon[m.status]}</div>
        </Link>
      ))}
    </div>
  );
}
