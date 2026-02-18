import { CheckSquare, Lightbulb, Link2, Scale } from "lucide-react";
import type { TopicSegment, ActionItem, Decision } from "../../lib/types";
import { formatDuration, getTopicColor, PRIORITY_COLORS, DECISION_COLOR } from "../../lib/timeline-utils";
import ConfidenceBadge from "./ConfidenceBadge";

interface Props {
  topic: TopicSegment;
  allActionItems: ActionItem[];
  allDecisions: Decision[];
}

export default function SegmentIntelligencePanel({
  topic,
  allActionItems,
  allDecisions,
}: Props) {
  // Filter action items and decisions within this topic's time range
  const topicActions = allActionItems.filter((ai) => {
    const t = ai.source_start_time ?? 0;
    return t >= topic.start_time && t < topic.end_time;
  });

  const topicDecisions = allDecisions.filter((d) => {
    const t = d.source_start_time ?? 0;
    return t >= topic.start_time && t < topic.end_time;
  });

  // Also include topic-level action items
  const nestedActions = topic.action_items ?? [];
  const allTopicActions = [
    ...topicActions,
    ...nestedActions.filter((na) => !topicActions.some((ta) => ta.id === na.id)),
  ];

  const color = getTopicColor(topic.order_index);
  const duration = topic.end_time - topic.start_time;

  return (
    <div
      className="border rounded-lg p-4 bg-[var(--lime-surface)] space-y-4"
      style={{ borderColor: color + "60" }}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <div
              className="w-2.5 h-2.5 rounded-sm shrink-0"
              style={{ backgroundColor: color }}
            />
            <h3 className="text-sm font-semibold text-[var(--lime-text)] truncate">
              {topic.title}
            </h3>
            <ConfidenceBadge confidence={topic.confidence} />
          </div>
          <p className="text-xs text-[var(--lime-text-muted)] mt-1 selectable">
            {topic.summary}
          </p>
          <p className="text-[10px] text-[var(--lime-text-dim)] mt-1">
            {formatDuration(topic.start_time)} — {formatDuration(topic.end_time)}
            <span className="ml-2">({formatDuration(duration)})</span>
          </p>
        </div>
      </div>

      {/* Action Items */}
      {allTopicActions.length > 0 && (
        <div>
          <p className="text-[10px] uppercase tracking-widest text-[var(--lime-text-dim)] mb-2 flex items-center gap-1.5">
            <CheckSquare size={10} />
            Action Items ({allTopicActions.length})
          </p>
          <div className="space-y-1.5">
            {allTopicActions.map((ai) => (
              <div
                key={ai.id}
                className="flex items-start gap-2 text-xs"
              >
                <span
                  className="inline-block w-1.5 h-1.5 rounded-full mt-1.5 shrink-0"
                  style={{ backgroundColor: PRIORITY_COLORS[ai.priority] }}
                />
                <span className="text-[var(--lime-text)] selectable flex-1">
                  {ai.description}
                </span>
                {ai.owner && (
                  <span className="text-[var(--lime-text-dim)] shrink-0">
                    → {ai.owner}
                  </span>
                )}
                {ai.below_threshold && <ConfidenceBadge confidence={ai.confidence} />}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Decisions */}
      {topicDecisions.length > 0 && (
        <div>
          <p className="text-[10px] uppercase tracking-widest text-[var(--lime-text-dim)] mb-2 flex items-center gap-1.5">
            <Scale size={10} />
            Decisions ({topicDecisions.length})
          </p>
          <div className="space-y-1.5">
            {topicDecisions.map((d) => (
              <div
                key={d.id}
                className="flex items-start gap-2 text-xs"
              >
                <span
                  className="inline-block w-1.5 h-1.5 shrink-0 mt-1.5"
                  style={{
                    backgroundColor: DECISION_COLOR,
                    clipPath: "polygon(50% 0%, 100% 50%, 50% 100%, 0% 50%)",
                  }}
                />
                <span className="text-[var(--lime-text)] selectable flex-1">
                  {d.description}
                </span>
                {d.below_threshold && <ConfidenceBadge confidence={d.confidence} />}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Insights */}
      {(topic.insights?.length ?? 0) > 0 && (
        <div>
          <p className="text-[10px] uppercase tracking-widest text-[var(--lime-text-dim)] mb-2 flex items-center gap-1.5">
            <Lightbulb size={10} />
            Insights ({topic.insights!.length})
          </p>
          <div className="space-y-1.5">
            {topic.insights!.map((ins) => (
              <div key={ins.id} className="flex items-start gap-2 text-xs">
                <Lightbulb
                  size={10}
                  className="mt-0.5 shrink-0"
                  style={{ color: "var(--accent)" }}
                />
                <span className="text-[var(--lime-text)] selectable">
                  {ins.title ?? ins.content}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Connections */}
      {(topic.connections?.length ?? 0) > 0 && (
        <div>
          <p className="text-[10px] uppercase tracking-widest text-[var(--lime-text-dim)] mb-2 flex items-center gap-1.5">
            <Link2 size={10} />
            Linked ({topic.connections!.length})
          </p>
          <div className="space-y-1">
            {topic.connections!.map((c, i) => (
              <div key={i} className="flex items-center gap-2 text-xs">
                <Link2 size={10} className="text-sky-400 shrink-0" />
                <span className="text-[var(--lime-text)] selectable">
                  {c.meeting_title ?? c.meeting_id}
                </span>
                <span className="text-[var(--lime-text-dim)]">{c.relationship}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Empty state */}
      {allTopicActions.length === 0 &&
        topicDecisions.length === 0 &&
        (topic.insights?.length ?? 0) === 0 &&
        (topic.connections?.length ?? 0) === 0 && (
          <p className="text-xs text-[var(--lime-text-dim)]">
            No action items, decisions, or insights in this segment.
          </p>
        )}
    </div>
  );
}
