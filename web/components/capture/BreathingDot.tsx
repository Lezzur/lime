"use client";

import { cn } from "@/lib/utils";
import type { UrgencyLevel } from "@/lib/types";

interface BreathingDotProps {
  urgency: UrgencyLevel;
  error?: boolean;
  offline?: boolean;
  onClick?: () => void;
  alertCount?: number;
}

const animationByUrgency: Record<UrgencyLevel, string> = {
  0: "animate-pulse-slow",
  1: "animate-breathe-calm",
  2: "animate-breathe-alert",
  3: "animate-breathe-urgent",
};

const sizeByUrgency: Record<UrgencyLevel, string> = {
  0: "w-8 h-8",
  1: "w-10 h-10",
  2: "w-14 h-14",
  3: "w-20 h-20",
};

const colorByState = (urgency: UrgencyLevel, error: boolean, offline: boolean) => {
  if (error) return "bg-red-500 shadow-red-500/50";
  if (offline) return "bg-amber-500 shadow-amber-500/50";
  if (urgency >= 3) return "bg-red-400 shadow-red-400/60";
  if (urgency >= 2) return "bg-orange-400 shadow-orange-400/50";
  if (urgency >= 1) return "bg-lime-400 shadow-lime-400/40";
  return "bg-zinc-600 shadow-zinc-600/30";
};

export function BreathingDot({
  urgency,
  error = false,
  offline = false,
  onClick,
  alertCount = 0,
}: BreathingDotProps) {
  return (
    <div className="relative flex items-center justify-center" onClick={onClick}>
      {/* Outer glow ring at high urgency */}
      {urgency >= 2 && !error && (
        <div
          className={cn(
            "absolute rounded-full opacity-30",
            animationByUrgency[urgency],
            urgency >= 3 ? "w-32 h-32 bg-red-400" : "w-24 h-24 bg-orange-400"
          )}
        />
      )}

      {/* Main dot */}
      <div
        className={cn(
          "rounded-full shadow-lg transition-all duration-500 cursor-pointer",
          animationByUrgency[urgency],
          sizeByUrgency[urgency],
          colorByState(urgency, error, offline)
        )}
      />

      {/* Alert count badge */}
      {alertCount > 0 && (
        <div className="absolute -top-1 -right-1 w-5 h-5 bg-white text-black text-xs font-bold rounded-full flex items-center justify-center">
          {alertCount > 9 ? "9+" : alertCount}
        </div>
      )}
    </div>
  );
}
