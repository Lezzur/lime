import type { ActionItem, Decision } from "../../lib/types";
import { timeToX, PRIORITY_COLORS, DECISION_COLOR } from "../../lib/timeline-utils";

interface Props {
  actionItems: ActionItem[];
  decisions: Decision[];
  totalDuration: number;
  trackWidth: number;
}

const MARKER_Y = 89;
const MARKER_R = 5;

export default function TimelineMarkers({
  actionItems,
  decisions,
  totalDuration,
  trackWidth,
}: Props) {
  return (
    <g>
      {/* Action item circles */}
      {actionItems.map((ai) => {
        const t = ai.source_start_time ?? 0;
        const x = timeToX(t, totalDuration, trackWidth);
        const color = PRIORITY_COLORS[ai.priority] ?? PRIORITY_COLORS.low;
        return (
          <g key={ai.id}>
            <circle
              cx={x}
              cy={MARKER_Y}
              r={MARKER_R}
              fill={color}
              fillOpacity={0.85}
              stroke={color}
              strokeWidth={0.5}
            />
            <title>{`[${ai.priority}] ${ai.description}`}</title>
          </g>
        );
      })}

      {/* Decision diamonds */}
      {decisions.map((d) => {
        const t = d.source_start_time ?? 0;
        const x = timeToX(t, totalDuration, trackWidth);
        const size = MARKER_R;
        return (
          <g key={d.id}>
            <polygon
              points={`${x},${MARKER_Y - size} ${x + size},${MARKER_Y} ${x},${MARKER_Y + size} ${x - size},${MARKER_Y}`}
              fill={DECISION_COLOR}
              fillOpacity={0.85}
              stroke={DECISION_COLOR}
              strokeWidth={0.5}
            />
            <title>{`Decision: ${d.description}`}</title>
          </g>
        );
      })}
    </g>
  );
}
