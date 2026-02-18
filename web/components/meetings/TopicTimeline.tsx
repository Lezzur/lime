"use client";

import { useState } from "react";
import type { MeetingNotes, TopicSegment } from "@/lib/types";
import { ConfidenceBadge } from "@/components/ui/ConfidenceBadge";
import { cn, formatDuration } from "@/lib/utils";

interface TopicTimelineProps {
  notes: MeetingNotes;
  duration: number;
  onSeek?: (time: number) => void;
}

export function TopicTimeline({ notes, duration, onSeek }: TopicTimelineProps) {
  const [selected, setSelected] = useState<string | null>(null);

  const totalDuration = duration || notes.topics.reduce((m, t) => Math.max(m, t.end_time), 0) || 1;

  const selectedTopic = notes.topics.find((t) => t.id === selected);

  // Heat map: map action items and insights to time ranges
  const hotspots = [
    ...notes.action_items.map((a) => a.source_start_time),
    ...notes.decisions.map((d) => d.source_start_time),
  ].filter((t): t is number => t !== null);

  return (
    <div className="space-y-6">
      {/* Horizontal timeline */}
      <div className="relative">
        {/* Track */}
        <div className="h-12 bg-zinc-900 rounded-xl overflow-hidden flex relative">
          {notes.topics.map((topic) => {
            const left = (topic.start_time / totalDuration) * 100;
            const width = ((topic.end_time - topic.start_time) / totalDuration) * 100;
            const isSelected = selected === topic.id;

            return (
              <div
                key={topic.id}
                className={cn(
                  "absolute h-full cursor-pointer transition-all border-r border-zinc-950",
                  isSelected
                    ? "bg-lime-600/50"
                    : "bg-zinc-800 hover:bg-zinc-700"
                )}
                style={{ left: `${left}%`, width: `${Math.max(width, 1)}%` }}
                onClick={() => {
                  setSelected(isSelected ? null : topic.id);
                  onSeek?.(topic.start_time);
                }}
                title={topic.title}
              />
            );
          })}

          {/* Hotspot markers */}
          {hotspots.map((t, i) => (
            <div
              key={i}
              className="absolute top-0 bottom-0 w-0.5 bg-lime-400/60 pointer-events-none"
              style={{ left: `${(t / totalDuration) * 100}%` }}
            />
          ))}
        </div>

        {/* Time labels */}
        <div className="flex justify-between mt-1 px-1">
          <span className="text-zinc-600 text-xs">0:00</span>
          <span className="text-zinc-600 text-xs">{formatDuration(totalDuration / 2)}</span>
          <span className="text-zinc-600 text-xs">{formatDuration(totalDuration)}</span>
        </div>
      </div>

      {/* Topic list */}
      <div className="space-y-2">
        {notes.topics.map((topic) => {
          const isSelected = selected === topic.id;
          const topicActions = notes.action_items.filter(
            (a) =>
              a.source_start_time !== null &&
              a.source_start_time >= topic.start_time &&
              a.source_start_time <= topic.end_time
          );
          const topicInsights = notes.insights.filter(
            (_, i) => i % notes.topics.length === notes.topics.indexOf(topic)
          );

          return (
            <div
              key={topic.id}
              className={cn(
                "rounded-xl border cursor-pointer transition-all",
                isSelected
                  ? "border-lime-700/50 bg-lime-950/20"
                  : "border-zinc-800 bg-zinc-900/50 hover:border-zinc-700"
              )}
              onClick={() => {
                setSelected(isSelected ? null : topic.id);
                onSeek?.(topic.start_time);
              }}
            >
              <div className="flex items-center gap-3 p-4">
                {/* Time range */}
                <div className="text-zinc-600 text-xs font-mono tabular-nums flex-shrink-0 w-24 text-right">
                  {formatDuration(topic.start_time)} – {formatDuration(topic.end_time)}
                </div>

                {/* Color bar */}
                <div
                  className={cn(
                    "w-1 self-stretch rounded-full flex-shrink-0",
                    isSelected ? "bg-lime-500" : "bg-zinc-700"
                  )}
                />

                <div className="flex-1 min-w-0">
                  <p className="text-zinc-200 text-sm font-medium">{topic.title}</p>
                  {topic.summary && (
                    <p className="text-zinc-500 text-xs mt-0.5 line-clamp-2">{topic.summary}</p>
                  )}
                </div>

                <div className="flex items-center gap-2 flex-shrink-0">
                  {topicActions.length > 0 && (
                    <span className="text-xs bg-zinc-800 text-zinc-400 px-1.5 py-0.5 rounded">
                      {topicActions.length} action{topicActions.length > 1 ? "s" : ""}
                    </span>
                  )}
                  <ConfidenceBadge confidence={topic.confidence} />
                </div>
              </div>

              {/* Expanded detail */}
              {isSelected && (topicActions.length > 0 || topicInsights.length > 0) && (
                <div className="border-t border-zinc-800 px-4 py-3 space-y-2">
                  {topicActions.map((a) => (
                    <div
                      key={a.id}
                      className="flex items-start gap-2 text-xs text-zinc-400"
                    >
                      <span className="text-lime-600 mt-0.5">→</span>
                      {a.description}
                      {a.owner && (
                        <span className="text-zinc-600">({a.owner})</span>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
