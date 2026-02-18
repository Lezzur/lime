import type { TopicSegment } from "../../lib/types";
import { timeToX, getTopicColor } from "../../lib/timeline-utils";

interface Props {
  topics: TopicSegment[];
  totalDuration: number;
  trackWidth: number;
  selectedTopicId: string | null;
  onSelectTopic: (id: string | null) => void;
}

const BLOCK_Y = 24;
const BLOCK_H = 40;

export default function TopicBlocks({
  topics,
  totalDuration,
  trackWidth,
  selectedTopicId,
  onSelectTopic,
}: Props) {
  return (
    <g>
      {topics.map((topic) => {
        const x = timeToX(topic.start_time, totalDuration, trackWidth);
        const w = timeToX(topic.end_time, totalDuration, trackWidth) - x;
        const color = getTopicColor(topic.order_index);
        const isSelected = selectedTopicId === topic.id;

        return (
          <g
            key={topic.id}
            className="cursor-pointer"
            onClick={() => onSelectTopic(isSelected ? null : topic.id)}
          >
            <rect
              x={x}
              y={BLOCK_Y}
              width={Math.max(w, 2)}
              height={BLOCK_H}
              rx={3}
              fill={color}
              fillOpacity={isSelected ? 0.4 : 0.2}
              stroke={isSelected ? color : "transparent"}
              strokeWidth={isSelected ? 1.5 : 0}
            />
            {/* Glow effect on selected */}
            {isSelected && (
              <rect
                x={x}
                y={BLOCK_Y}
                width={Math.max(w, 2)}
                height={BLOCK_H}
                rx={3}
                fill="none"
                stroke={color}
                strokeWidth={1}
                opacity={0.5}
                filter="url(#glow)"
              />
            )}
            {/* Topic label if wide enough */}
            {w > 40 && (
              <text
                x={x + 6}
                y={BLOCK_Y + BLOCK_H / 2 + 1}
                dominantBaseline="middle"
                fill="var(--lime-text)"
                fontSize={10}
                fontWeight={500}
                opacity={0.9}
                clipPath={`inset(0 ${Math.max(0, w - 12)}px 0 0)`}
              >
                <tspan>
                  {topic.title.length > Math.floor(w / 6)
                    ? topic.title.slice(0, Math.floor(w / 6) - 1) + "…"
                    : topic.title}
                </tspan>
              </text>
            )}
          </g>
        );
      })}
    </g>
  );
}
