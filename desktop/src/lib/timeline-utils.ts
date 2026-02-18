import type { ActionItem, Decision } from "./types";

// --- Color palette for topic blocks ---

const TOPIC_COLORS = [
  "#84cc16", // lime-500
  "#65a30d", // lime-600
  "#a3e635", // lime-400
  "#4d7c0f", // lime-700
  "#bef264", // lime-300
  "#3f6212", // lime-800
  "#d9f99d", // lime-200
  "#365314", // lime-900
];

export function getTopicColor(orderIndex: number): string {
  return TOPIC_COLORS[orderIndex % TOPIC_COLORS.length];
}

// --- Coordinate mapping ---

export function timeToX(time: number, totalDuration: number, trackWidth: number): number {
  if (totalDuration <= 0) return 0;
  return (time / totalDuration) * trackWidth;
}

// --- Duration formatting ---

export function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

// --- Tick interval ---

export function getTickInterval(totalDuration: number): number {
  if (totalDuration <= 120) return 15;
  if (totalDuration <= 300) return 30;
  if (totalDuration <= 900) return 60;
  if (totalDuration <= 1800) return 120;
  if (totalDuration <= 3600) return 300;
  return 600;
}

// --- Heat map calculation ---

export interface HeatBucket {
  start: number;
  end: number;
  intensity: number; // 0..1 normalized
}

const BUCKET_COUNT = 50;

export function calculateHeatMap(
  totalDuration: number,
  actionItems: ActionItem[],
  decisions: Decision[],
): HeatBucket[] {
  if (totalDuration <= 0) return [];

  const bucketSize = totalDuration / BUCKET_COUNT;
  const raw = new Array<number>(BUCKET_COUNT).fill(0);

  const priorityWeight: Record<string, number> = { high: 3, medium: 2, low: 1 };

  for (const ai of actionItems) {
    const t = ai.source_start_time ?? 0;
    const idx = Math.min(Math.floor(t / bucketSize), BUCKET_COUNT - 1);
    raw[idx] += priorityWeight[ai.priority] ?? 1;
  }

  for (const d of decisions) {
    const t = d.source_start_time ?? 0;
    const idx = Math.min(Math.floor(t / bucketSize), BUCKET_COUNT - 1);
    raw[idx] += 2;
  }

  const max = Math.max(...raw, 1);

  return raw.map((val, i) => ({
    start: i * bucketSize,
    end: (i + 1) * bucketSize,
    intensity: val / max,
  }));
}

// --- Heat map color interpolation ---

export function heatColor(intensity: number): string {
  // lime (cool) → amber (hot)
  // lime:  rgb(132, 204, 22) → amber: rgb(245, 158, 11)
  const r = Math.round(132 + (245 - 132) * intensity);
  const g = Math.round(204 + (158 - 204) * intensity);
  const b = Math.round(22 + (11 - 22) * intensity);
  const a = 0.1 + 0.8 * intensity;
  return `rgba(${r}, ${g}, ${b}, ${a.toFixed(2)})`;
}

// --- Priority colors for markers ---

export const PRIORITY_COLORS: Record<string, string> = {
  high: "#ef4444",   // red-500
  medium: "#f59e0b", // amber-500
  low: "#84cc16",    // lime-500
};

export const DECISION_COLOR = "#3b82f6"; // blue-500
