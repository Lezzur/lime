"use client";

import { useCallback, useEffect, useState } from "react";
import { BreathingDot } from "./BreathingDot";
import { useGestures } from "@/hooks/useGestures";
import { cn } from "@/lib/utils";
import type { CaptureAlert, UrgencyLevel } from "@/lib/types";
import { formatDuration } from "@/lib/utils";

interface ActiveModeProps {
  urgency: UrgencyLevel;
  alerts: CaptureAlert[];
  duration: number;
  error?: boolean;
  offline?: boolean;
  onBookmark: () => void;
  onPriorityFlag: () => void;
  onVoiceCapture: (active: boolean) => void;
  onDismissAlert: (id: string) => void;
}

export function ActiveMode({
  urgency,
  alerts,
  duration,
  error = false,
  offline = false,
  onBookmark,
  onPriorityFlag,
  onVoiceCapture,
  onDismissAlert,
}: ActiveModeProps) {
  const [showAlerts, setShowAlerts] = useState(false);

  // Haptic feedback when urgency escalates
  useEffect(() => {
    if (typeof navigator === "undefined" || !("vibrate" in navigator)) return;
    if (urgency === 3) {
      navigator.vibrate([100, 50, 100, 50, 200]);
    } else if (urgency === 2) {
      navigator.vibrate([80, 40, 80]);
    }
  }, [urgency]);

  const { handleTouchStart, handleTouchEnd, handleTouchMove } = useGestures({
    onSingleTap: () => {
      setShowAlerts((v) => !v);
      onBookmark();
    },
    onDoubleTap: () => {
      onPriorityFlag();
      if (typeof navigator !== "undefined" && "vibrate" in navigator) {
        navigator.vibrate([30, 20, 30]);
      }
    },
    onLongPress: () => onVoiceCapture(true),
  });

  const handleTouchEndExtended = useCallback(
    (e: React.TouchEvent) => {
      handleTouchEnd(e);
    },
    [handleTouchEnd]
  );

  const urgencyBg: Record<UrgencyLevel, string> = {
    0: "bg-black",
    1: "bg-zinc-950",
    2: "bg-zinc-950",
    3: "bg-black",
  };

  return (
    <div
      className={cn(
        "fixed inset-0 flex flex-col items-center justify-center touch-none select-none transition-colors duration-1000",
        urgencyBg[urgency]
      )}
      onTouchStart={handleTouchStart}
      onTouchEnd={handleTouchEndExtended}
      onTouchMove={handleTouchMove}
      style={{ touchAction: "none" }}
    >
      {/* Recording duration — minimal, top center */}
      <div className="absolute top-6 left-1/2 -translate-x-1/2 text-zinc-600 text-xs font-mono">
        {formatDuration(duration)}
      </div>

      {/* Offline/Error status */}
      {offline && (
        <div className="absolute top-6 right-4 text-amber-500 text-xs">OFFLINE</div>
      )}
      {error && (
        <div className="absolute top-6 right-4 text-red-500 text-xs">ERROR</div>
      )}

      {/* Central breathing dot */}
      <BreathingDot
        urgency={urgency}
        error={error}
        offline={offline}
        onClick={() => setShowAlerts((v) => !v)}
        alertCount={alerts.filter((a) => !showAlerts).length}
      />

      {/* Swipe-up hint at high urgency */}
      {urgency >= 2 && !showAlerts && (
        <div className="absolute bottom-16 left-1/2 -translate-x-1/2 text-zinc-600 text-xs">
          tap to see alerts
        </div>
      )}

      {/* Alert panel — slides up when tapped */}
      {showAlerts && alerts.length > 0 && (
        <div className="absolute bottom-0 left-0 right-0 bg-zinc-900/95 backdrop-blur-sm rounded-t-2xl p-4 max-h-64 overflow-y-auto">
          <div className="w-8 h-1 bg-zinc-700 rounded-full mx-auto mb-4" />
          <div className="space-y-2">
            {alerts.map((alert) => (
              <div
                key={alert.id}
                className={cn(
                  "flex items-start gap-3 p-3 rounded-lg",
                  alert.urgency >= 3
                    ? "bg-red-900/40"
                    : alert.urgency >= 2
                    ? "bg-orange-900/40"
                    : "bg-zinc-800/60"
                )}
                onClick={() => onDismissAlert(alert.id)}
              >
                <div
                  className={cn(
                    "w-1.5 h-1.5 rounded-full mt-1.5 flex-shrink-0",
                    alert.urgency >= 3
                      ? "bg-red-400"
                      : alert.urgency >= 2
                      ? "bg-orange-400"
                      : "bg-lime-400"
                  )}
                />
                <p className="text-white text-sm leading-relaxed">{alert.message}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Empty alerts panel */}
      {showAlerts && alerts.length === 0 && (
        <div className="absolute bottom-0 left-0 right-0 bg-zinc-900/95 rounded-t-2xl p-6 text-center">
          <div className="w-8 h-1 bg-zinc-700 rounded-full mx-auto mb-4" />
          <p className="text-zinc-500 text-sm">No alerts yet</p>
        </div>
      )}
    </div>
  );
}
