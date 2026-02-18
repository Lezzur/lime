import { useRef, useEffect, useState } from "react";
import type { TopicSegment, ActionItem, Decision } from "../../lib/types";
import type { HeatBucket } from "../../lib/timeline-utils";
import TimeAxis from "./TimeAxis";
import TopicBlocks from "./TopicBlocks";
import HeatMapBar from "./HeatMapBar";
import TimelineMarkers from "./TimelineMarkers";

interface Props {
  topics: TopicSegment[];
  actionItems: ActionItem[];
  decisions: Decision[];
  heatBuckets: HeatBucket[];
  totalDuration: number;
  selectedTopicId: string | null;
  onSelectTopic: (id: string | null) => void;
}

const SVG_HEIGHT = 100;
const MIN_PX_PER_MINUTE = 8;

export default function TimelineTrack({
  topics,
  actionItems,
  decisions,
  heatBuckets,
  totalDuration,
  selectedTopicId,
  onSelectTopic,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [containerWidth, setContainerWidth] = useState(600);

  useEffect(() => {
    if (!containerRef.current) return;

    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setContainerWidth(entry.contentRect.width);
      }
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  const durationMinutes = totalDuration / 60;
  const trackWidth = Math.max(containerWidth, MIN_PX_PER_MINUTE * durationMinutes);
  const needsScroll = trackWidth > containerWidth;

  return (
    <div
      ref={containerRef}
      className={`w-full ${needsScroll ? "overflow-x-auto" : ""}`}
    >
      <svg
        width={trackWidth}
        height={SVG_HEIGHT}
        viewBox={`0 0 ${trackWidth} ${SVG_HEIGHT}`}
        className="block"
      >
        {/* Glow filter for selected topic */}
        <defs>
          <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        <TimeAxis totalDuration={totalDuration} trackWidth={trackWidth} />
        <TopicBlocks
          topics={topics}
          totalDuration={totalDuration}
          trackWidth={trackWidth}
          selectedTopicId={selectedTopicId}
          onSelectTopic={onSelectTopic}
        />
        <HeatMapBar
          buckets={heatBuckets}
          totalDuration={totalDuration}
          trackWidth={trackWidth}
        />
        <TimelineMarkers
          actionItems={actionItems}
          decisions={decisions}
          totalDuration={totalDuration}
          trackWidth={trackWidth}
        />
      </svg>
    </div>
  );
}
