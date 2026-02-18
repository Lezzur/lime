"use client";

import { useCallback, useEffect, useState } from "react";
import { useAudioRecorder } from "@/hooks/useAudioRecorder";
import { useSilenceDetection } from "@/hooks/useSilenceDetection";
import { useOfflineQueue } from "@/hooks/useOfflineQueue";
import { cn, formatDuration } from "@/lib/utils";
import { Mic, Square, MicOff } from "lucide-react";

interface VoiceMemoRecorderProps {
  onRecorded?: (blob: Blob, duration: number) => void;
}

type RecordingState = "idle" | "recording" | "stopping";

export function VoiceMemoRecorder({ onRecorded }: VoiceMemoRecorderProps) {
  const [state, setState] = useState<RecordingState>("idle");
  const [error, setError] = useState<string | null>(null);
  const { isRecording, duration, start, stop, getStream } = useAudioRecorder();
  const { isOnline, enqueue } = useOfflineQueue();

  const { start: startSilence, stop: stopSilence } = useSilenceDetection({
    silenceDuration: 15000,
    silenceThreshold: 0.008,
    onSilence: () => {
      if (state === "recording") handleStop();
    },
  });

  const handleStart = useCallback(async () => {
    setError(null);
    const stream = await start();
    if (!stream) {
      setError("Microphone access denied");
      return;
    }
    setState("recording");
    startSilence(stream);
  }, [start, startSilence]);

  const handleStop = useCallback(async () => {
    if (state !== "recording") return;
    setState("stopping");
    stopSilence();
    const blob = await stop();

    if (blob && blob.size > 0) {
      onRecorded?.(blob, duration);
      if (!isOnline) {
        await enqueue({
          id: `memo-${Date.now()}`,
          created_at: Date.now(),
          blob,
          type: "voice_memo",
        });
      } else {
        // Upload immediately
        const formData = new FormData();
        formData.append("audio", blob, "memo.webm");
        formData.append("duration", String(duration));
        try {
          await fetch("/api/lime/voice-memo", { method: "POST", body: formData });
        } catch {
          // Queue for later
          await enqueue({
            id: `memo-${Date.now()}`,
            created_at: Date.now(),
            blob,
            type: "voice_memo",
          });
        }
      }
    }

    setState("idle");
  }, [state, stop, stopSilence, duration, onRecorded, isOnline, enqueue]);

  // Volume-key shortcut via keyboard (simulates volume-down triple press in PWA context)
  useEffect(() => {
    let keyPressCount = 0;
    let keyTimer: ReturnType<typeof setTimeout> | null = null;

    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "AudioVolumeDown" || e.key === "VolumeDown") {
        keyPressCount++;
        if (keyTimer) clearTimeout(keyTimer);
        keyTimer = setTimeout(() => {
          keyPressCount = 0;
        }, 800);
        if (keyPressCount >= 3 && state === "idle") {
          keyPressCount = 0;
          handleStart();
        }
      }
    };

    window.addEventListener("keydown", handleKey);
    return () => {
      window.removeEventListener("keydown", handleKey);
      if (keyTimer) clearTimeout(keyTimer);
    };
  }, [state, handleStart]);

  return (
    <div className="flex flex-col items-center gap-6 p-8">
      {/* Record button */}
      <button
        onClick={state === "idle" ? handleStart : handleStop}
        disabled={state === "stopping"}
        className={cn(
          "w-20 h-20 rounded-full flex items-center justify-center transition-all duration-200",
          state === "recording"
            ? "bg-red-600 shadow-lg shadow-red-900/50 scale-110"
            : state === "stopping"
            ? "bg-zinc-700 scale-95"
            : "bg-zinc-800 hover:bg-zinc-700 active:scale-95"
        )}
      >
        {state === "recording" ? (
          <Square className="w-7 h-7 text-white" />
        ) : state === "stopping" ? (
          <MicOff className="w-7 h-7 text-zinc-400" />
        ) : (
          <Mic className="w-8 h-8 text-white" />
        )}
      </button>

      {/* Duration / status */}
      {state === "recording" && (
        <div className="text-center">
          <p className="text-red-400 font-mono text-xl">{formatDuration(duration)}</p>
          <p className="text-zinc-500 text-xs mt-1">
            Stops after 15s of silence · tap to end early
          </p>
        </div>
      )}

      {state === "idle" && !error && (
        <p className="text-zinc-600 text-sm text-center">
          Tap to record &nbsp;·&nbsp; 3× volume-down to start
        </p>
      )}

      {error && (
        <div className="flex items-center gap-2 text-red-400 text-sm">
          <MicOff className="w-4 h-4" />
          {error}
        </div>
      )}

      {!isOnline && (
        <p className="text-amber-500 text-xs">Offline — memo will sync when connected</p>
      )}
    </div>
  );
}
