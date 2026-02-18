import type { HeatBucket } from "../../lib/timeline-utils";
import { timeToX, heatColor } from "../../lib/timeline-utils";

interface Props {
  buckets: HeatBucket[];
  totalDuration: number;
  trackWidth: number;
}

const BAR_Y = 68;
const BAR_H = 10;

export default function HeatMapBar({ buckets, totalDuration, trackWidth }: Props) {
  if (buckets.length === 0) return null;

  return (
    <g>
      {buckets.map((bucket, i) => {
        const x = timeToX(bucket.start, totalDuration, trackWidth);
        const w = timeToX(bucket.end, totalDuration, trackWidth) - x;
        return (
          <rect
            key={i}
            x={x}
            y={BAR_Y}
            width={Math.max(w, 1)}
            height={BAR_H}
            fill={heatColor(bucket.intensity)}
            rx={i === 0 ? 2 : 0}
            ry={i === 0 ? 2 : 0}
          />
        );
      })}
      {/* Border outline */}
      <rect
        x={0}
        y={BAR_Y}
        width={trackWidth}
        height={BAR_H}
        rx={2}
        fill="none"
        stroke="var(--lime-border)"
        strokeWidth={0.5}
      />
    </g>
  );
}
