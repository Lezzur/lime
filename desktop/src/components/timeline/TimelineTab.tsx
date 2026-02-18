import { useMeetingStore } from "../../stores/meetingStore";
import { calculateHeatMap } from "../../lib/timeline-utils";
import ConfidenceBadge from "./ConfidenceBadge";
import SegmentIntelligencePanel from "./SegmentIntelligencePanel";
import TimelineTrack from "./TimelineTrack";

interface Props {
  totalDuration: number;
}

export default function TimelineTab({ totalDuration }: Props) {
  const { selectedMeetingNotes, selectedTopicId, setSelectedTopicId } = useMeetingStore();

  if (!selectedMeetingNotes) {
    return (
      <div className="flex items-center justify-center p-12 text-[var(--lime-text-muted)] text-sm">
        No analysis data available.
      </div>
    );
  }

  const { topics, action_items, decisions } = selectedMeetingNotes;
  const duration = totalDuration || topics[topics.length - 1]?.end_time || 0;

  if (topics.length === 0) {
    return (
      <div className="flex items-center justify-center p-12 text-[var(--lime-text-muted)] text-sm">
        No topic segments available yet.
      </div>
    );
  }

  const sortedTopics = [...topics].sort((a, b) => a.order_index - b.order_index);
  const heatBuckets = calculateHeatMap(duration, action_items, decisions);
  const selectedTopic = selectedTopicId
    ? topics.find((t) => t.id === selectedTopicId)
    : null;

  return (
    <div className="p-6 space-y-4">
      {/* Overall confidence */}
      {selectedMeetingNotes.overall_confidence != null && (
        <div className="flex items-center gap-2">
          <span className="text-[10px] uppercase tracking-widest text-[var(--lime-text-dim)]">
            Analysis Confidence
          </span>
          <ConfidenceBadge
            confidence={selectedMeetingNotes.overall_confidence}
            threshold={0.7}
          />
          {selectedMeetingNotes.overall_confidence >= 0.7 && (
            <span className="text-[10px] text-emerald-400">
              {Math.round(selectedMeetingNotes.overall_confidence * 100)}%
            </span>
          )}
        </div>
      )}

      {/* Legend */}
      <div className="flex items-center gap-4 text-[10px] text-[var(--lime-text-dim)]">
        <span className="flex items-center gap-1">
          <span className="inline-block w-2 h-2 rounded-full bg-red-500" />
          High priority
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block w-2 h-2 rounded-full bg-amber-500" />
          Medium
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block w-2 h-2 rounded-full bg-lime-500" />
          Low
        </span>
        <span className="flex items-center gap-1">
          <span
            className="inline-block w-2 h-2 bg-blue-500"
            style={{ clipPath: "polygon(50% 0%, 100% 50%, 50% 100%, 0% 50%)" }}
          />
          Decision
        </span>
      </div>

      {/* SVG Timeline */}
      <TimelineTrack
        topics={sortedTopics}
        actionItems={action_items}
        decisions={decisions}
        heatBuckets={heatBuckets}
        totalDuration={duration}
        selectedTopicId={selectedTopicId}
        onSelectTopic={setSelectedTopicId}
      />

      {/* Intelligence panel for selected topic */}
      {selectedTopic && (
        <SegmentIntelligencePanel
          topic={selectedTopic}
          allActionItems={action_items}
          allDecisions={decisions}
        />
      )}
    </div>
  );
}
