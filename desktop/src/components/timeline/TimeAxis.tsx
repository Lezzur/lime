import { formatDuration, getTickInterval, timeToX } from "../../lib/timeline-utils";

interface Props {
  totalDuration: number;
  trackWidth: number;
}

export default function TimeAxis({ totalDuration, trackWidth }: Props) {
  if (totalDuration <= 0) return null;

  const interval = getTickInterval(totalDuration);
  const ticks: number[] = [];
  for (let t = 0; t <= totalDuration; t += interval) {
    ticks.push(t);
  }

  return (
    <g>
      {ticks.map((t) => {
        const x = timeToX(t, totalDuration, trackWidth);
        return (
          <g key={t}>
            <line
              x1={x}
              y1={12}
              x2={x}
              y2={20}
              stroke="var(--lime-border)"
              strokeWidth={1}
            />
            <text
              x={x}
              y={10}
              textAnchor="middle"
              fill="var(--lime-text-dim)"
              fontSize={9}
              fontFamily="monospace"
            >
              {formatDuration(t)}
            </text>
          </g>
        );
      })}
      {/* Baseline */}
      <line
        x1={0}
        y1={20}
        x2={trackWidth}
        y2={20}
        stroke="var(--lime-border)"
        strokeWidth={1}
      />
    </g>
  );
}
