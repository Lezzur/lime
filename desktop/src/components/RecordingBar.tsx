import { useEffect, useState } from "react";
import { Mic, MicOff, ChevronDown, Monitor } from "lucide-react";
import { useMeetingStore } from "../stores/meetingStore";
import { api } from "../lib/api";

export default function RecordingBar() {
  const {
    isRecording,
    activeMeetingId,
    audioDevices,
    selectedDeviceId,
    startRecording,
    stopRecording,
    setAudioDevices,
    setSelectedDevice,
    setMeetings,
  } = useMeetingStore();

  const [loading, setLoading] = useState(false);
  const [deviceOpen, setDeviceOpen] = useState(false);
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    api.getDevices().then(setAudioDevices).catch(console.error);
  }, [setAudioDevices]);

  // Recording timer
  useEffect(() => {
    if (!isRecording) {
      setElapsed(0);
      return;
    }
    const t = setInterval(() => setElapsed((s) => s + 1), 1000);
    return () => clearInterval(t);
  }, [isRecording]);

  const formatElapsed = (s: number) => {
    const m = Math.floor(s / 60).toString().padStart(2, "0");
    const sec = (s % 60).toString().padStart(2, "0");
    return `${m}:${sec}`;
  };

  const inputDevices = audioDevices.filter((d) => d.direction === "input" || !d.direction);
  const selectedDevice = inputDevices.find((d) => d.id === selectedDeviceId) ?? inputDevices[0];

  async function handleToggle() {
    if (loading) return;
    setLoading(true);
    try {
      if (isRecording && activeMeetingId) {
        await api.stopMeeting(activeMeetingId);
        stopRecording();
        // Refresh meetings list
        const updated = await api.getMeetings();
        setMeetings(updated);
      } else {
        const res = await api.startMeeting(selectedDevice?.id);
        startRecording(res.id);
      }
    } catch (err) {
      console.error("Recording toggle failed:", err);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex items-center gap-3 px-4 py-2.5 border-b border-[var(--lime-border)] bg-[var(--lime-surface)]">
      {/* Device picker */}
      <div className="relative">
        <button
          onClick={() => !isRecording && setDeviceOpen((o) => !o)}
          disabled={isRecording}
          className="flex items-center gap-2 px-3 py-1.5 rounded-md text-xs bg-[var(--lime-surface-2)] border border-[var(--lime-border)] hover:border-[#404040] disabled:opacity-40 disabled:cursor-not-allowed transition-colors min-w-[160px]"
        >
          {selectedDevice?.name?.includes("system") || selectedDevice?.name?.includes("Stereo Mix") ? (
            <Monitor size={12} className="text-[var(--lime-text-muted)] shrink-0" />
          ) : (
            <Mic size={12} className="text-[var(--lime-text-muted)] shrink-0" />
          )}
          <span className="truncate text-[var(--lime-text-muted)] flex-1 text-left">
            {selectedDevice?.name ?? "Select device"}
          </span>
          <ChevronDown size={10} className="text-[var(--lime-text-dim)] shrink-0" />
        </button>

        {deviceOpen && (
          <div className="absolute top-full left-0 mt-1 z-50 bg-[var(--lime-surface-2)] border border-[var(--lime-border)] rounded-md shadow-xl min-w-[220px] py-1">
            {inputDevices.length === 0 && (
              <p className="px-3 py-2 text-xs text-[var(--lime-text-muted)]">No devices found</p>
            )}
            {inputDevices.map((dev) => (
              <button
                key={dev.id}
                onClick={() => {
                  setSelectedDevice(dev.id);
                  setDeviceOpen(false);
                }}
                className={`w-full flex items-center gap-2 px-3 py-2 text-xs text-left hover:bg-white/5 transition-colors ${
                  selectedDeviceId === dev.id ? "text-white" : "text-[var(--lime-text-muted)]"
                }`}
              >
                <Mic size={11} className="shrink-0" />
                <span className="truncate flex-1">{dev.name}</span>
                {dev.is_default && (
                  <span className="text-[10px] text-[var(--lime-text-dim)]">default</span>
                )}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Start / Stop button */}
      <button
        onClick={handleToggle}
        disabled={loading}
        className={`flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-medium transition-all disabled:opacity-50 ${
          isRecording
            ? "bg-red-500/20 text-red-400 border border-red-500/40 hover:bg-red-500/30"
            : "text-[var(--accent-text)] hover:opacity-90"
        }`}
        style={isRecording ? {} : { backgroundColor: "var(--accent)" }}
      >
        {isRecording ? (
          <>
            <MicOff size={12} />
            Stop
          </>
        ) : (
          <>
            <Mic size={12} />
            Record
          </>
        )}
      </button>

      {/* Timer */}
      {isRecording && (
        <div className="flex items-center gap-2 text-xs text-red-400">
          <span className="h-1.5 w-1.5 rounded-full bg-red-500 animate-pulse" />
          {formatElapsed(elapsed)}
        </div>
      )}

      {/* Close dropdown on outside click */}
      {deviceOpen && (
        <div className="fixed inset-0 z-40" onClick={() => setDeviceOpen(false)} />
      )}
    </div>
  );
}
