"use client";

import { useEffect, useState } from "react";
import { use } from "react";
import {
  getMeetingNotes,
  getTranscript,
  getMeeting,
  getAudioUrl,
} from "@/lib/api";
import type { Meeting, MeetingNotes, TranscriptSegment } from "@/lib/types";
import { ExecutiveSummary } from "@/components/meetings/ExecutiveSummary";
import { TranscriptView } from "@/components/meetings/TranscriptView";
import { TopicTimeline } from "@/components/meetings/TopicTimeline";
import { AudioPlayer } from "@/components/audio/AudioPlayer";
import { formatTimestamp, formatDuration } from "@/lib/utils";
import { ArrowLeft, Loader, AlertCircle, Mic, Monitor } from "lucide-react";
import Link from "next/link";

type Tab = "summary" | "timeline" | "transcript";

export default function MeetingDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [meeting, setMeeting] = useState<Meeting | null>(null);
  const [notes, setNotes] = useState<MeetingNotes | null>(null);
  const [segments, setSegments] = useState<TranscriptSegment[]>([]);
  const [activeTab, setActiveTab] = useState<Tab>("summary");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [seekTime, setSeekTime] = useState<number | undefined>();
  const [audioTime, setAudioTime] = useState(0);

  useEffect(() => {
    Promise.all([getMeeting(id), getMeetingNotes(id), getTranscript(id)])
      .then(([m, n, s]) => {
        setMeeting(m);
        setNotes(n);
        setSegments(s);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader className="w-6 h-6 text-zinc-500 animate-spin" />
      </div>
    );
  }

  if (error || !meeting) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen gap-4">
        <AlertCircle className="w-8 h-8 text-zinc-600" />
        <p className="text-zinc-500 text-sm">{error ?? "Meeting not found"}</p>
        <Link href="/meetings" className="text-lime-400 text-sm hover:underline">
          Back to meetings
        </Link>
      </div>
    );
  }

  const tabs: { id: Tab; label: string }[] = [
    { id: "summary", label: "Summary" },
    { id: "timeline", label: "Timeline" },
    { id: "transcript", label: "Transcript" },
  ];

  return (
    <div className="min-h-screen">
      {/* Header */}
      <div className="sticky top-0 z-10 bg-zinc-950/95 backdrop-blur border-b border-zinc-900">
        <div className="px-6 py-4 flex items-start gap-4">
          <Link
            href="/meetings"
            className="text-zinc-500 hover:text-zinc-300 transition-colors mt-0.5"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div className="flex-1 min-w-0">
            <h1 className="text-white font-semibold truncate">
              {meeting.title ?? "Untitled Meeting"}
            </h1>
            <div className="flex items-center gap-3 mt-1 text-zinc-500 text-xs">
              {meeting.audio_source === "system" ? (
                <Monitor className="w-3.5 h-3.5" />
              ) : (
                <Mic className="w-3.5 h-3.5" />
              )}
              <span>{formatTimestamp(meeting.started_at)}</span>
              {meeting.duration_seconds && (
                <span>{formatDuration(meeting.duration_seconds)}</span>
              )}
            </div>
          </div>
        </div>

        {/* Tab bar */}
        <div className="flex px-6 gap-1 pb-0">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2 text-sm rounded-t-lg transition-colors ${
                activeTab === tab.id
                  ? "text-white border-b-2 border-lime-500"
                  : "text-zinc-500 hover:text-zinc-300"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Audio player */}
      <div className="px-6 py-4 border-b border-zinc-900">
        <AudioPlayer
          src={getAudioUrl(id)}
          currentSegmentTime={seekTime}
          onTimeUpdate={setAudioTime}
        />
      </div>

      {/* Content */}
      <div className="px-6 py-6">
        {activeTab === "summary" && notes && (
          <ExecutiveSummary
            notes={notes}
            onSeekTranscript={(t) => {
              setSeekTime(t);
              setActiveTab("transcript");
            }}
          />
        )}

        {activeTab === "timeline" && notes && (
          <TopicTimeline
            notes={notes}
            duration={meeting.duration_seconds ?? 0}
            onSeek={(t) => {
              setSeekTime(t);
            }}
          />
        )}

        {activeTab === "transcript" && (
          <TranscriptView
            meetingId={id}
            segments={segments}
            topics={notes?.topics}
            onSeek={setSeekTime}
            highlightTime={audioTime}
          />
        )}

        {!notes && activeTab !== "transcript" && (
          <div className="text-center py-12 text-zinc-500">
            <p className="text-sm">No analysis yet for this meeting.</p>
          </div>
        )}
      </div>
    </div>
  );
}
