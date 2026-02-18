import { useState } from "react";
import { ChevronRight, Clock, CheckSquare, Lightbulb, Link2 } from "lucide-react";
import type { TopicSegment } from "../lib/types";

interface Props {
  topics: TopicSegment[];
  totalDuration?: number;
}

function formatTime(s: number) {
  const m = Math.floor(s / 60).toString().padStart(2, "0");
  const sec = Math.floor(s % 60).toString().padStart(2, "0");
  return `${m}:${sec}`;
}

function TopicCard({ topic, index, totalDuration }: { topic: TopicSegment; index: number; totalDuration: number }) {
  const [expanded, setExpanded] = useState(false);

  const duration = topic.end_time - topic.start_time;
  const durationPct = totalDuration > 0 ? (duration / totalDuration) * 100 : 0;

  const hasLayers =
    (topic.insights?.length ?? 0) > 0 ||
    (topic.connections?.length ?? 0) > 0 ||
    (topic.action_items?.length ?? 0) > 0;

  const accent = "var(--accent)";

  return (
    <div className="relative">
      {/* Timeline connector */}
      <div className="absolute left-5 top-10 bottom-0 w-px bg-[var(--lime-border)]" />

      <div className="flex gap-3">
        {/* Index bubble */}
        <div
          className="relative z-10 flex-shrink-0 h-10 w-10 rounded-full flex items-center justify-center text-xs font-bold border-2"
          style={{ borderColor: accent, color: accent, backgroundColor: "var(--lime-bg)" }}
        >
          {index + 1}
        </div>

        {/* Card */}
        <div className="flex-1 mb-4">
          <button
            onClick={() => setExpanded((e) => !e)}
            className="w-full text-left"
            disabled={!hasLayers}
          >
            <div className="flex items-start justify-between gap-2 p-3 rounded-lg bg-[var(--lime-surface-2)] border border-[var(--lime-border)] hover:border-[#404040] transition-colors">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <h4 className="text-sm font-medium text-[var(--lime-text)] truncate">
                    {topic.title}
                  </h4>
                  {hasLayers && (
                    <ChevronRight
                      size={12}
                      className={`text-[var(--lime-text-dim)] shrink-0 transition-transform ${expanded ? "rotate-90" : ""}`}
                    />
                  )}
                </div>
                <p className="text-xs text-[var(--lime-text-muted)] mt-0.5 selectable line-clamp-2">
                  {topic.summary}
                </p>
                <div className="flex items-center gap-3 mt-2">
                  <span className="flex items-center gap-1 text-[10px] text-[var(--lime-text-dim)]">
                    <Clock size={9} />
                    {formatTime(topic.start_time)} — {formatTime(topic.end_time)}
                  </span>
                  <span className="text-[10px] text-[var(--lime-text-dim)]">
                    {Math.round(durationPct)}% of meeting
                  </span>
                </div>
              </div>

              {/* Mini badges */}
              <div className="flex flex-col items-end gap-1 shrink-0">
                {(topic.action_items?.length ?? 0) > 0 && (
                  <span className="flex items-center gap-1 text-[10px] text-amber-400">
                    <CheckSquare size={9} />
                    {topic.action_items!.length}
                  </span>
                )}
                {(topic.insights?.length ?? 0) > 0 && (
                  <span className="flex items-center gap-1 text-[10px]" style={{ color: accent }}>
                    <Lightbulb size={9} />
                    {topic.insights!.length}
                  </span>
                )}
                {(topic.connections?.length ?? 0) > 0 && (
                  <span className="flex items-center gap-1 text-[10px] text-sky-400">
                    <Link2 size={9} />
                    {topic.connections!.length}
                  </span>
                )}
              </div>
            </div>
          </button>

          {/* Expandable intelligence layers */}
          {expanded && hasLayers && (
            <div className="mt-2 ml-2 pl-3 border-l-2 space-y-3" style={{ borderColor: accent + "40" }}>
              {/* Action Items */}
              {(topic.action_items?.length ?? 0) > 0 && (
                <div>
                  <p className="text-[10px] uppercase tracking-widest text-[var(--lime-text-dim)] mb-1.5">
                    Actions
                  </p>
                  <div className="space-y-1">
                    {topic.action_items!.map((a) => (
                      <div key={a.id} className="flex items-start gap-2 text-xs">
                        <CheckSquare size={11} className="text-amber-400 mt-0.5 shrink-0" />
                        <span className="text-[var(--lime-text)] selectable">{a.description}</span>
                        {a.owner && (
                          <span className="text-[var(--lime-text-dim)] shrink-0">→ {a.owner}</span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Insights */}
              {(topic.insights?.length ?? 0) > 0 && (
                <div>
                  <p className="text-[10px] uppercase tracking-widest text-[var(--lime-text-dim)] mb-1.5">
                    Insights
                  </p>
                  <div className="space-y-1">
                    {topic.insights!.map((ins) => (
                      <div key={ins.id} className="flex items-start gap-2 text-xs">
                        <Lightbulb size={11} className="mt-0.5 shrink-0" style={{ color: accent }} />
                        <span className="text-[var(--lime-text)] selectable">{ins.content}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Connections */}
              {(topic.connections?.length ?? 0) > 0 && (
                <div>
                  <p className="text-[10px] uppercase tracking-widest text-[var(--lime-text-dim)] mb-1.5">
                    Linked Meetings
                  </p>
                  <div className="space-y-1">
                    {topic.connections!.map((c, i) => (
                      <div key={i} className="flex items-center gap-2 text-xs">
                        <Link2 size={11} className="text-sky-400 shrink-0" />
                        <span className="text-[var(--lime-text)] selectable">
                          {c.meeting_title ?? c.meeting_id}
                        </span>
                        <span className="text-[var(--lime-text-dim)]">{c.relationship}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function TopicTimeline({ topics, totalDuration }: Props) {
  const duration = totalDuration ?? (topics[topics.length - 1]?.end_time ?? 0);

  if (topics.length === 0) {
    return (
      <div className="flex items-center justify-center p-12 text-[var(--lime-text-muted)] text-sm">
        No topic segments available yet.
      </div>
    );
  }

  return (
    <div className="p-6">
      {/* Horizontal bar overview */}
      <div className="flex gap-px rounded-full overflow-hidden h-2 mb-6">
        {topics.map((topic, i) => {
          const pct =
            duration > 0
              ? ((topic.end_time - topic.start_time) / duration) * 100
              : 100 / topics.length;
          return (
            <div
              key={topic.id}
              className="h-full transition-all"
              style={{
                width: `${pct}%`,
                opacity: 0.3 + (i / topics.length) * 0.7,
                backgroundColor: "var(--accent)",
              }}
              title={topic.title}
            />
          );
        })}
      </div>

      {/* Topic cards */}
      <div>
        {topics
          .sort((a, b) => a.order_index - b.order_index)
          .map((topic, i) => (
            <TopicCard key={topic.id} topic={topic} index={i} totalDuration={duration} />
          ))}
      </div>
    </div>
  );
}
