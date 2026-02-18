import { AlertTriangle } from "lucide-react";

interface Props {
  confidence: number;
  threshold?: number;
}

export default function ConfidenceBadge({ confidence, threshold = 0.7 }: Props) {
  if (confidence >= threshold) return null;

  const pct = Math.round(confidence * 100);

  return (
    <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[10px] font-medium bg-amber-500/15 text-amber-400 border border-amber-500/25">
      <AlertTriangle size={9} />
      {pct}%
    </span>
  );
}
