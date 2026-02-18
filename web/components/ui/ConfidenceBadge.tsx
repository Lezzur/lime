import { cn } from "@/lib/utils";

interface ConfidenceBadgeProps {
  confidence: number;
  showAlways?: boolean;
  className?: string;
}

export function ConfidenceBadge({
  confidence,
  showAlways = false,
  className,
}: ConfidenceBadgeProps) {
  const pct = Math.round(confidence * 100);
  const threshold = 0.7;

  if (!showAlways && confidence >= threshold) return null;

  return (
    <span
      className={cn(
        "inline-flex items-center px-1.5 py-0.5 rounded text-xs font-mono font-medium border",
        confidence >= 0.7
          ? "text-green-400 border-green-800 bg-green-950/50"
          : confidence >= 0.5
          ? "text-yellow-400 border-yellow-800 bg-yellow-950/50"
          : "text-red-400 border-red-800 bg-red-950/50",
        className
      )}
      title={`${pct}% confidence`}
    >
      {pct}%
    </span>
  );
}
