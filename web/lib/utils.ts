import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import { formatDistanceToNow, format } from "date-fns";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDuration(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  if (h > 0) return `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  return `${m}:${String(s).padStart(2, "0")}`;
}

export function formatTimestamp(isoString: string): string {
  const d = new Date(isoString);
  return format(d, "MMM d, yyyy h:mm a");
}

export function formatRelative(isoString: string): string {
  return formatDistanceToNow(new Date(isoString), { addSuffix: true });
}

export function confidenceColor(confidence: number): string {
  if (confidence >= 0.8) return "text-green-400";
  if (confidence >= 0.5) return "text-yellow-400";
  return "text-red-400";
}

export function confidenceBg(confidence: number): string {
  if (confidence >= 0.8) return "bg-green-900/30 border-green-700/50";
  if (confidence >= 0.5) return "bg-yellow-900/30 border-yellow-700/50";
  return "bg-red-900/30 border-red-700/50";
}

export function urgencyToBreatheDuration(urgency: number): string {
  if (urgency >= 3) return "0.8s";
  if (urgency >= 2) return "1.5s";
  if (urgency >= 1) return "2.5s";
  return "4s";
}
