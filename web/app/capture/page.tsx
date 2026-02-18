"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { DiscreetMode } from "@/components/capture/DiscreetMode";
import { ActiveMode } from "@/components/capture/ActiveMode";
import { useAudioRecorder } from "@/hooks/useAudioRecorder";
import { useWakeWord } from "@/hooks/useWakeWord";
import { useOfflineQueue } from "@/hooks/useOfflineQueue";
import type { CaptureAlert, CaptureMode, UrgencyLevel } from "@/lib/types";
import { startMeeting, stopMeeting } from "@/lib/api";
import { cn } from "@/lib/utils";

// Bootstrap screen shown before entering capture
function StartScreen({
  onStart,
}: {
  onStart: (mode: CaptureMode) => void;
}) {
  return (
    <div className="fixed inset-0 bg-black flex flex-col items-center justify-center gap-8 p-8">
      <div className="text-center">
        <h1 className="text-white text-2xl font-light tracking-widest mb-2">LIME</h1>
        <p className="text-zinc-500 text-sm">capture mode</p>
      </div>

      <div className="flex flex-col gap-4 w-full max-w-xs">
        <button
          onClick={() => onStart("discreet")}
          className="w-full py-4 bg-zinc-900 text-white rounded-2xl text-sm tracking-wide border border-zinc-800 active:bg-zinc-800 transition-colors"
        >
          Discreet Mode
          <p className="text-zinc-500 text-xs mt-1">black screen • tap gestures</p>
        </button>
        <button
          onClick={() => onStart("active")}
          className="w-full py-4 bg-zinc-900 text-white rounded-2xl text-sm tracking-wide border border-zinc-800 active:bg-zinc-800 transition-colors"
        >
          Active Mode
          <p className="text-zinc-500 text-xs mt-1">breathing dot • live alerts</p>
        </button>
      </div>

      <p className="text-zinc-700 text-xs text-center">
        Single tap = bookmark &nbsp;·&nbsp; Double tap = priority &nbsp;·&nbsp; Hold = voice note
      </p>
    </div>
  );
}

export default function CapturePage() {
  const [phase, setPhase] = useState<"start" | "recording">("start");
  const [mode, setMode] = useState<CaptureMode>("discreet");
  const [urgency, setUrgency] = useState<UrgencyLevel>(1);
  const [alerts, setAlerts] = useState<CaptureAlert[]>([]);
  const [meetingId, setMeetingId] = useState<string | null>(null);
  const [error, setError] = useState(false);
  const [wakeWordEnabled, setWakeWordEnabled] = useState(false);

  const { isRecording, duration, start: startRecorder, stop: stopRecorder } = useAudioRecorder();
  const { isOnline, enqueue } = useOfflineQueue();
  const alertIdRef = useRef(0);

  // Wake word mode switching
  useWakeWord({
    wakeWord: "koda",
    enabled: wakeWordEnabled && phase === "recording",
    onModeSwitch: (newMode) => setMode(newMode),
  });

  // Simulate urgency escalation via WebSocket in real integration
  // For now, expose a test escalation on long press of the dot
  const addAlert = useCallback((message: string, level: UrgencyLevel = 1) => {
    const id = String(++alertIdRef.current);
    setAlerts((prev) => [{ id, timestamp: Date.now(), type: "insight", message, urgency: level }, ...prev]);
    setUrgency((prev) => Math.max(prev, level) as UrgencyLevel);
  }, []);

  const handleStart = useCallback(
    async (selectedMode: CaptureMode) => {
      setMode(selectedMode);
      setPhase("recording");
      setError(false);

      const stream = await startRecorder();
      if (!stream) {
        setError(true);
        setPhase("start");
        return;
      }

      if (isOnline) {
        try {
          const res = await startMeeting("microphone");
          setMeetingId(res.meeting_id);
        } catch {
          // Offline fallback — will upload when back online
        }
      }

      setWakeWordEnabled(true);
    },
    [startRecorder, isOnline]
  );

  const handleStop = useCallback(async () => {
    setWakeWordEnabled(false);
    const blob = await stopRecorder();

    if (meetingId && isOnline) {
      try {
        await stopMeeting(meetingId);
      } catch {
        // ignore
      }
    } else if (blob) {
      await enqueue({
        id: `offline-${Date.now()}`,
        created_at: Date.now(),
        blob,
        type: "meeting",
        meeting_title: `Meeting ${new Date().toLocaleDateString()}`,
      });
    }

    setPhase("start");
    setMeetingId(null);
    setAlerts([]);
    setUrgency(1);
  }, [stopRecorder, meetingId, isOnline, enqueue]);

  const handleBookmark = useCallback(() => {
    addAlert("Bookmark added", 1);
  }, [addAlert]);

  const handlePriorityFlag = useCallback(() => {
    addAlert("Priority flag set", 2);
  }, [addAlert]);

  const handleVoiceCapture = useCallback((active: boolean) => {
    if (active) addAlert("Voice note recording…", 1);
  }, [addAlert]);

  const handleDismissAlert = useCallback((id: string) => {
    setAlerts((prev) => {
      const remaining = prev.filter((a) => a.id !== id);
      const maxUrgency = remaining.reduce<number>((m, a) => Math.max(m, a.urgency), 0) as UrgencyLevel;
      setUrgency(maxUrgency || 1);
      return remaining;
    });
  }, []);

  // Stop button overlay (small, visible in both modes)
  const StopButton = () => (
    <button
      onClick={handleStop}
      className={cn(
        "fixed bottom-8 right-6 z-50 w-12 h-12 rounded-full flex items-center justify-center transition-all",
        mode === "discreet"
          ? "bg-zinc-900/10 text-zinc-800"
          : "bg-zinc-900 text-zinc-400 border border-zinc-700"
      )}
    >
      <div className="w-4 h-4 rounded bg-current" />
    </button>
  );

  if (phase === "start") {
    return <StartScreen onStart={handleStart} />;
  }

  return (
    <>
      {mode === "discreet" ? (
        <DiscreetMode
          onBookmark={handleBookmark}
          onPriorityFlag={handlePriorityFlag}
          onVoiceCapture={handleVoiceCapture}
          error={error}
          offline={!isOnline}
        />
      ) : (
        <ActiveMode
          urgency={urgency}
          alerts={alerts}
          duration={duration}
          error={error}
          offline={!isOnline}
          onBookmark={handleBookmark}
          onPriorityFlag={handlePriorityFlag}
          onVoiceCapture={handleVoiceCapture}
          onDismissAlert={handleDismissAlert}
        />
      )}
      <StopButton />
    </>
  );
}
